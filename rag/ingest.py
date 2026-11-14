import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from chunker import build_policy_chunks

load_dotenv()

META_KEYS = ("clause_id", "doc_id", "doc_version",
             "section_type", "page", "heading")


def file_sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def load_documents():
    """Documents to index: (doc_id, path, version, chunk_builder)."""
    policy_path = os.environ.get("POLICY_PDF")
    if not policy_path or not os.path.isfile(policy_path):
        raise FileNotFoundError(
            "POLICY_PDF must point to the policy PDF; check your .env file"
        )
    docs = [("policy", policy_path,
             os.environ.get("POLICY_VERSION", "unknown"), build_policy_chunks)]

    daycare_path = os.environ.get("DAYCARE_PDF")
    if daycare_path and os.path.exists(daycare_path):
        from daycare_chunker import build_daycare_chunks
        docs.append(("daycare", daycare_path,
                     os.environ.get("DAYCARE_VERSION", "unknown"),
                     build_daycare_chunks))
    else:
        print("WARNING: day-care procedure list is not configured or not found; "
              "day-care procedure retrieval will return no results")
    return docs


def index_document(col, model, doc_id, path, version, builder):
    chunks = builder(path, doc_id, version)
    new_ids = {c["id"] for c in chunks}
    existing = set(col.get(where={"doc_id": doc_id})["ids"])

    stale = list(existing - new_ids)      # content changed or vanished
    if stale:
        col.delete(ids=stale)

    to_add = [c for c in chunks if c["id"] not in existing]   # only NEW content
    if to_add:
        embs = model.encode([c["text"] for c in to_add],
                            normalize_embeddings=True,
                            show_progress_bar=True).tolist()
        col.add(
            ids=[c["id"] for c in to_add],
            embeddings=embs,
            documents=[c["text"] for c in to_add],
            metadatas=[{k: c[k] for k in META_KEYS} for c in to_add],
        )
    print(f"{doc_id}: {len(chunks)} chunks, {len(to_add)} newly embedded, "
          f"{len(stale)} stale removed")

    entry = {"doc_id": doc_id, "file": path, "file_sha": file_sha(path),
             "version": version, "chunks": len(chunks)}
    return entry, len(to_add)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true",
                    help="delete the whole collection and start fresh")
    ap.add_argument("--reembed", metavar="DOC_ID",
                    help="re-embed ONE document (e.g. policy or daycare) "
                         "without touching the others")
    args = ap.parse_args()

    start = time.time()
    client = chromadb.PersistentClient(path=os.environ["CHROMA_DIR"])
    name = os.environ["COLLECTION_NAME"]
    if args.rebuild:
        try:
            client.delete_collection(name)
        except Exception:
            pass
    col = client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})
    model = SentenceTransformer(os.environ["EMBED_MODEL"])

    documents = load_documents()
    if args.reembed and args.reembed not in {row[0] for row in documents}:
        ap.error(f"'{args.reembed}' is not configured in the current corpus")
    if args.reembed:
        col.delete(where={"doc_id": args.reembed})
        print(f"removed all chunks of '{args.reembed}', re-indexing it now")

    entries, embedded_total = [], 0
    for doc_id, path, version, builder in documents:
        entry, n_added = index_document(col, model, doc_id, path, version, builder)
        entries.append(entry)
        embedded_total += n_added

    secs = time.time() - start
    manifest = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "embed_model": os.environ["EMBED_MODEL"],
        "documents": entries,
        "total_chunks_in_index": col.count(),
        "chunks_embedded_this_run": embedded_total,
        "seconds": round(secs, 2),
        "chunks_per_second": round(embedded_total / secs, 2) if secs else 0,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/index_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print("done:", manifest)


if __name__ == "__main__":
    main()
