
import re

from agents.schemas import CoverageInvestigation
from agents.tools import lookup_clause


def normalize_text(value: str) -> str:
    """Normalize text for basic word-level comparisons."""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


SECTION_ALIASES = {
    "cover": "coverage",
    "coverage": "coverage",
    "waiting_period": "waiting period",
    "waiting period": "waiting period",
    "exclusion": "exclusions",
    "exclusions": "exclusions",
    "sublimit": "sub-limits",
    "sub-limits": "sub-limits",
    "daycare_procedure": "day-care procedure",
    "day-care procedure": "day-care procedure",
    "definition": "definitions",
    "definitions": "definitions",
    "annexure": "annexure",
}


def get_section(clause: dict) -> str:
    """Support both the old mock format and the real RAG format."""

    section_type = clause.get("section_type")

    if isinstance(section_type, str) and section_type.strip():
        return SECTION_ALIASES.get(
            section_type.strip().lower(),
            section_type.strip().replace("_", " ").lower(),
        )

    section = clause.get("section")

    if isinstance(section, str):
        return SECTION_ALIASES.get(
            section.strip().lower(),
            section.strip().lower(),
        )

    return ""


def verify_investigation(
    investigation: CoverageInvestigation,
) -> dict:
    """
    Verify retrieved policy evidence against the canonical RAG corpus.

    Checks:
    1. At least one clause was retrieved.
    2. Clause identifiers, text and page numbers are valid.
    3. Clause metadata matches the canonical corpus.
    4. Duplicate citations are rejected.
    5. Coverage evidence is relevant to the requested procedure.
    6. Explicitly unresolved investigation checks are rejected.

    This is rule-based verification, not semantic or LLM-based verification.
    """

    errors = []
    clauses = investigation.retrieved_clauses

    if not clauses:
        errors.append("No policy clauses were retrieved")

    clause_ids = set()
    duplicate_ids = set()
    canonical_matches = {}

    # -----------------------------------------------------
    # 1. Validate retrieved clauses against the RAG corpus
    # -----------------------------------------------------

    for clause in clauses:
        if not isinstance(clause, dict):
            errors.append(
                "Retrieved clause is not a valid dictionary"
            )
            continue

        clause_id = clause.get("clause_id")
        text = clause.get("text")
        page = clause.get("page")
        section = get_section(clause)

        if not isinstance(clause_id, str) or not clause_id.strip():
            errors.append("Clause is missing its identifier")
            continue

        clause_id = clause_id.strip()

        if clause_id in clause_ids:
            duplicate_ids.add(clause_id)

        clause_ids.add(clause_id)

        if not isinstance(text, str) or not text.strip():
            errors.append(
                f"Clause {clause_id} has missing or empty text"
            )

        if (
            not isinstance(page, int)
            or isinstance(page, bool)
            or page <= 0
        ):
            errors.append(
                f"Clause {clause_id} has an invalid or missing page number"
            )

        if not section:
            errors.append(
                f"Clause {clause_id} is missing its section"
            )

        # Look up the original clause in the actual RAG corpus.
        canonical_clause = lookup_clause(clause_id)

        if canonical_clause is None:
            errors.append(
                f"Unsupported clause citation: {clause_id}"
            )
            continue

        canonical_matches[clause_id] = canonical_clause

        canonical_section = get_section(canonical_clause)

        if text != canonical_clause.get("text"):
            errors.append(
                f"Clause {clause_id} text does not match the policy corpus"
            )

        if page != canonical_clause.get("page"):
            errors.append(
                f"Clause {clause_id} page does not match the policy corpus"
            )

        if section != canonical_section:
            errors.append(
                f"Clause {clause_id} section does not match the policy corpus"
            )

    # -----------------------------------------------------
    # 2. Detect duplicate clause identifiers
    # -----------------------------------------------------

    for clause_id in sorted(duplicate_ids):
        errors.append(
            f"Duplicate clause identifier: {clause_id}"
        )

    # -----------------------------------------------------
    # 3. Identify sections actually retrieved
    # -----------------------------------------------------

    found_sections = {
        get_section(clause)
        for clause in clauses
        if isinstance(clause, dict) and get_section(clause)
    }

    # Do not require every possible policy section to appear.
    # Missing evidence is handled through unresolved_checks
    # when a particular check is actually required.

    # -----------------------------------------------------
    # 4. Check unresolved investigation items
    # -----------------------------------------------------

    if investigation.unresolved_checks:
        errors.extend(investigation.unresolved_checks)

    # -----------------------------------------------------
    # 5. Extract the requested procedure from investigation notes
    # -----------------------------------------------------

    procedure = None

    accepted_prefixes = (
        "Procedure investigated: ",
        "Procedure under investigation: ",
    )

    for note in investigation.investigation_notes:
        for prefix in accepted_prefixes:
            if note.startswith(prefix):
                procedure = note[len(prefix):].rstrip(".").strip()
                break

        if procedure:
            break

    if not procedure:
        errors.append(
            "Procedure information is missing from investigation notes"
        )

    # -----------------------------------------------------
    # 6. Verify coverage evidence relevance
    # -----------------------------------------------------

    coverage_clauses = [
        clause
        for clause in clauses
        if isinstance(clause, dict)
        and get_section(clause) == "coverage"
    ]

    if not coverage_clauses:
        errors.append(
            "No coverage clause available for relevance checking"
        )

    elif procedure:
        procedure_words = {
            word
            for word in normalize_text(procedure).split()
            if len(word) > 2
        }

        relevant_clause_found = False

        for clause in coverage_clauses:
            clause_text = clause.get("text", "")

            if not isinstance(clause_text, str):
                continue

            clause_words = set(
                normalize_text(clause_text).split()
            )

            if procedure_words.intersection(clause_words):
                relevant_clause_found = True
                break

        if not relevant_clause_found:
            errors.append(
                f"No coverage clause appears relevant to procedure: "
                f"{procedure}"
            )

    # -----------------------------------------------------
    # 7. Collect verified citation identifiers
    # -----------------------------------------------------

    verified_clause_ids = []

    for clause in clauses:
        if not isinstance(clause, dict):
            continue

        clause_id = clause.get("clause_id")

        if not isinstance(clause_id, str):
            continue

        clause_id = clause_id.strip()

        canonical_clause = canonical_matches.get(clause_id)

        if canonical_clause is None:
            continue

        citation_matches = (
            clause.get("text") == canonical_clause.get("text")
            and clause.get("page") == canonical_clause.get("page")
            and get_section(clause) == get_section(canonical_clause)
            and isinstance(clause.get("text"), str)
            and bool(clause.get("text").strip())
            and isinstance(clause.get("page"), int)
            and not isinstance(clause.get("page"), bool)
            and clause.get("page") > 0
            and bool(get_section(clause))
        )

        if citation_matches and clause_id not in duplicate_ids:
            verified_clause_ids.append(clause_id)

    return {
        "verified": len(errors) == 0,
        "errors": errors,
        "verified_clause_ids": sorted(
            set(verified_clause_ids)
        ),
        "sections_found": sorted(found_sections),
    }
