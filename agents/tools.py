
"""
Policy retrieval tools for the pre-authorisation agents.

Uses Person 1's ChromaDB RAG module instead of synthetic policy clauses.
Request-field lookup remains available to the agents.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from agents.schemas import PreAuthRequest


# ---------------------------------------------------------
# RAG configuration
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAG_DIR = PROJECT_ROOT / "rag"
RAG_ENV_FILE = RAG_DIR / ".env"

if not RAG_ENV_FILE.exists():
    raise FileNotFoundError(
        f"RAG configuration not found: {RAG_ENV_FILE}. "
        "Create rag/.env using rag/.env.example."
    )

# Load the RAG configuration regardless of the current
# working directory.
load_dotenv(RAG_ENV_FILE, override=False)

# Person 1's CHROMA_DIR is relative to the rag directory.
configured_chroma_dir = Path(
    os.environ.get("CHROMA_DIR", "./chroma_db")
)

if not configured_chroma_dir.is_absolute():
    configured_chroma_dir = RAG_DIR / configured_chroma_dir

os.environ["CHROMA_DIR"] = str(configured_chroma_dir.resolve())


# Import the actual RAG tools.
from rag.tools import (  # noqa: E402
    search_corpus,
    get_clause,
    get_clause_parts,
    search_modifiers,
    check_waiting_period,
    check_daycare,
    search_daycare_list,
    list_documents,
)


# ---------------------------------------------------------
# Section-name compatibility
# ---------------------------------------------------------

SECTION_NAMES = {
    "cover": "Coverage",
    "waiting_period": "Waiting Period",
    "exclusion": "Exclusions",
    "sublimit": "Sub-limits",
    "definition": "Definitions",
    "annexure": "Annexure",
    "daycare_procedure": "Day-care Procedure",
}


def normalize_clause(clause: dict | None) -> dict | None:
    """
    Convert a Person 1 RAG result into the common clause
    structure expected by Person 2's agents.

    Original RAG fields are retained.
    """

    if clause is None:
        return None

    normalized = dict(clause)

    section_type = normalized.get("section_type")

    normalized["section"] = SECTION_NAMES.get(
        section_type,
        str(section_type or "Unknown").replace("_", " ").title(),
    )

    return normalized


# ---------------------------------------------------------
# Policy retrieval
# ---------------------------------------------------------

def search_policy(
    query: str,
    section_type: str | None = None,
    k: int = 5,
) -> list[dict]:
    """
    Search the actual indexed policy corpus.

    Optional section_type values:
    cover, waiting_period, exclusion, sublimit,
    definition, annexure, daycare_procedure.
    """

    results = search_corpus(
        query,
        section_type=section_type,
        k=k,
    )

    return [
        normalized
        for result in results
        if (normalized := normalize_clause(result)) is not None
    ]


def lookup_clause(clause_id: str) -> dict | None:
    """
    Retrieve an exact clause chunk from the actual RAG corpus.
    """

    return normalize_clause(get_clause(clause_id))


def lookup_clause_parts(clause_id: str) -> list[dict]:
    """
    Retrieve all chunks belonging to a clause.

    Useful for long policy provisions that span multiple chunks.
    """

    return [
        normalized
        for result in get_clause_parts(clause_id)
        if (normalized := normalize_clause(result)) is not None
    ]


# ---------------------------------------------------------
# Additional RAG investigation tools
# ---------------------------------------------------------

def search_policy_modifiers(
    query: str,
    k: int = 3,
) -> list[dict]:
    """
    Search waiting-period, exclusion and sub-limit provisions.
    """

    return [
        normalized
        for result in search_modifiers(query, k=k)
        if (normalized := normalize_clause(result)) is not None
    ]


def check_policy_waiting_period(condition: str) -> dict:
    """
    Check whether the condition is mentioned in waiting-period
    provisions in the indexed policy.
    """

    result = check_waiting_period(condition)

    result["matches"] = [
        normalized
        for clause in result.get("matches", [])
        if (normalized := normalize_clause(clause)) is not None
    ]

    return result


def check_procedure_daycare(
    procedure: str,
    k: int = 3,
) -> dict:
    """
    Check the indexed day-care list.

    A not_found result is not proof of exclusion.
    """

    result = check_daycare(procedure, k=k)

    result["matches"] = [
        normalized
        for clause in result.get("matches", [])
        if (normalized := normalize_clause(clause)) is not None
    ]

    result["nearest"] = [
        normalized
        for clause in result.get("nearest", [])
        if (normalized := normalize_clause(clause)) is not None
    ]

    return result


# ---------------------------------------------------------
# Hospital request lookup
# ---------------------------------------------------------

def lookup_request_field(
    request: PreAuthRequest,
    field_name: str,
):
    """
    Retrieve a specific field from the hospital request.
    """

    if field_name not in PreAuthRequest.model_fields:
        raise ValueError(
            f"Unknown request field: {field_name}"
        )

    return getattr(request, field_name)
