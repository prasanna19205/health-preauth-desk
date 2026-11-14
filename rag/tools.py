"""Retrieval tools for the policy and day-care procedure corpus.

Each result includes a clause identifier, source document/version, page, and
the exact retrieved text so an agent can cite only evidence it has seen.
"""
import os
from functools import lru_cache

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

DEFAULT_K = 5
MAX_K = 20
SECTION_TYPES = {
    "cover", "waiting_period", "exclusion", "sublimit", "definition",
    "annexure", "daycare_procedure",
}


@lru_cache(maxsize=1)
def _model():
    return SentenceTransformer(os.environ["EMBED_MODEL"])


@lru_cache(maxsize=1)
def _collection():
    client = chromadb.PersistentClient(path=os.environ["CHROMA_DIR"])
    return client.get_collection(os.environ["COLLECTION_NAME"])


def _limit(k):
    try:
        value = int(k)
    except (TypeError, ValueError) as exc:
        raise ValueError("k must be an integer") from exc
    if value < 1:
        raise ValueError("k must be at least 1")
    return min(value, MAX_K)


def _format(res):
    ids = (res.get("ids") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    distances = (res.get("distances") or [[]])[0]
    out = []
    for clause_id, metadata, document, distance in zip(ids, metas, docs, distances):
        out.append({
            "clause_id": metadata.get("clause_id", clause_id),
            "doc_id": metadata.get("doc_id"),
            "doc_version": metadata.get("doc_version"),
            "section_type": metadata.get("section_type"),
            "page": metadata.get("page"),
            "heading": metadata.get("heading"),
            "text": document,
            "score": round(1 - distance, 4),  # cosine similarity; higher is closer
        })
    return out


def _where(section_type=None, doc_id=None, exclude_annexures=True):
    clauses = []
    if section_type:
        if section_type not in SECTION_TYPES:
            raise ValueError(f"Unknown section_type: {section_type}")
        clauses.append({"section_type": section_type})
    elif exclude_annexures:
        clauses.append({"section_type": {"$ne": "annexure"}})
    if doc_id:
        clauses.append({"doc_id": doc_id})
    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def _search(query, where, k):
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    collection = _collection()
    if collection.count() == 0:
        return []
    query_args = {
        "query_embeddings": _model().encode(
            [query.strip()], normalize_embeddings=True
        ).tolist(),
        "n_results": min(_limit(k), collection.count()),
    }
    if where:
        query_args["where"] = where
    try:
        return _format(collection.query(**query_args))
    except Exception as exc:
        # Chroma rejects n_results when a filter matches fewer records than the
        # corpus. Retry with smaller limits, preserving the original error if
        # the filter itself is invalid or the database is unavailable.
        if "larger than" not in str(exc).lower() and "n_results" not in str(exc):
            raise
        for limit in range(query_args["n_results"] - 1, 0, -1):
            query_args["n_results"] = limit
            try:
                return _format(collection.query(**query_args))
            except Exception:
                continue
        return []


def search_corpus(query, section_type=None, k=DEFAULT_K, doc_id=None):
    """Semantic retrieval from indexed policy or procedure documents.

    section_type may be cover, waiting_period, exclusion, sublimit, definition,
    annexure, or daycare_procedure. Annexures are excluded by default when no
    explicit section type is supplied.
    """
    return _search(query, _where(section_type, doc_id), k)


def get_clause(clause_id):
    """Return an exact indexed clause, or None when it is not in the corpus."""
    if not isinstance(clause_id, str) or not clause_id.strip():
        raise ValueError("clause_id must be a non-empty string")
    res = _collection().get(where={"clause_id": clause_id.strip()})
    if not res.get("ids"):
        return None
    return _format({
        "ids": [res["ids"]], "metadatas": [res["metadatas"]],
        "documents": [res["documents"]], "distances": [[0.0] * len(res["ids"])],
    })[0]


def search_modifiers(query, k=3):
    """Retrieve provisions that may change coverage: waits, exclusions, limits."""
    results = []
    for section_type in ("waiting_period", "exclusion", "sublimit"):
        results.extend(search_corpus(query, section_type=section_type, k=k))
    return sorted(results, key=lambda result: result["score"], reverse=True)


def search_daycare_list(procedure, k=3):
    """Search indexed day-care procedures; returns [] if none are indexed."""
    return search_corpus(
        procedure, section_type="daycare_procedure", doc_id="daycare", k=k
    )


def list_documents():
    """Return indexed document ids, versions, and chunk counts for diagnostics."""
    records = _collection().get(include=["metadatas"])
    summary = {}
    for metadata in records.get("metadatas") or []:
        doc_id = metadata.get("doc_id", "unknown")
        row = summary.setdefault(doc_id, {
            "doc_id": doc_id, "doc_version": metadata.get("doc_version"),
            "chunks": 0,
        })
        row["chunks"] += 1
    return list(summary.values())
