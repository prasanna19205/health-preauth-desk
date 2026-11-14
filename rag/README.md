# Care Supreme policy RAG module

Person 1 deliverable: PDF text extraction and clause chunking, local sentence
embeddings, persistent Chroma storage, and retrieval tools that return clause
citations with source document, version, page, and verbatim retrieved text.

## Current corpus

- Expected local source: `data/raw/policy.pdf`, Care Supreme policy, UIN
  `CHIHLIP27061V032627`, 83 pages. The supplied policy PDF and generated Chroma
  database are kept out of GitHub; place the PDF at that path before indexing.
  In the original local workspace, this PDF was indexed as 204 chunks.
- The separate Care day-care procedures list is not present in this checkout.
  Ingestion supports an optional `data/raw/daycare.pdf`, but do not use a list
  from a different product/UIN as if it were the policy-specific source. The
  [insurer's day-care page](https://www.careinsurance.com/health-insurance/daycare-treatment-in-health-insurance)
  describes a 541-procedure list and points to an updateable list; verify the
  version/source before using it for decisions.

## Setup and indexing

Use Python 3.10+ and install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `POLICY_PDF`, `POLICY_VERSION`, `CHROMA_DIR`, `COLLECTION_NAME`, and
`EMBED_MODEL` in `.env`. `DAYCARE_PDF` and `DAYCARE_VERSION` are optional; when
the matching list is available, put it at the configured path and ingest it.
Paths are relative to the directory from which the command is run.

```powershell
python ingest.py
python ingest.py --rebuild
python ingest.py --reembed policy
```

The first run downloads the Sentence Transformers model if it is not cached.
Ingestion is incremental: unchanged chunk IDs are retained, changed/removed
chunks are deleted, and only new chunks are embedded. `--rebuild` replaces the
entire configured collection.

## Retrieval API for the agent module

`tools.py` provides:

- `search_corpus(query, section_type=None, k=5, doc_id=None)` — semantic search.
- `search_modifiers(query, k=3)` — searches waiting periods, exclusions, and
  sub-limits separately, then ranks the combined results.
- `get_clause(clause_id)` — exact clause lookup, returning `None` if absent.
- `search_daycare_list(procedure, k=3)` — procedure search; returns an empty
  list until `doc_id="daycare"` has been indexed.
- `list_documents()` — indexed document IDs, versions, and chunk counts.

Every search result contains `clause_id`, `doc_id`, `doc_version`, `page`,
`heading`, `section_type`, `text`, and cosine similarity `score`. Cite only the
returned text and treat an empty result as missing evidence requiring review.

## Day-care list ingestion

The optional chunker preserves page numbers and groups numbered/bulleted
procedure entries. Configure `DAYCARE_PDF` and `DAYCARE_VERSION`, then run
`python ingest.py`. Day-care hits use `section_type="daycare_procedure"` and
clause IDs such as `daycare:p12:item4`. This parser supports text-layer PDFs; a
scanned document needs OCR before ingestion.

## Evidence and limitations

The `data/index_manifest.json` records the source hash, document versions,
chunk counts, and embedding model used for the last indexing run. The current
policy corpus can support clause retrieval; it does not by itself make a
coverage decision or establish that a procedure is eligible. The supplied
project brief specifically calls for the distant waiting-period and exclusion
provisions to be retrieved alongside apparent coverage clauses.
