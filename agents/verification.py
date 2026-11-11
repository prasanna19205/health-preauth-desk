
import re

from agents.schemas import CoverageInvestigation
from agents.tools import lookup_clause


REQUIRED_SECTIONS = {
    "coverage",
    "waiting period",
    "exclusions",
    "sub-limits",
    "room eligibility",
}


def normalize_text(value: str) -> str:
    """Normalize text for basic word-level comparisons."""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def verify_investigation(
    investigation: CoverageInvestigation,
) -> dict:
    """
    Verify:
    1. Clauses exist.
    2. Clause metadata is valid.
    3. Clause IDs are unique.
    4. Clauses match the actual policy corpus.
    5. Required policy sections are present.
    6. No investigation checks remain unresolved.
    7. Coverage evidence is relevant to the procedure.

    This is rule-based verification, not semantic or LLM-based
    verification.
    """

    errors = []
    clauses = investigation.retrieved_clauses

    # CHECK 1: At least one clause must be retrieved.
    if not clauses:
        errors.append("No policy clauses were retrieved")

    clause_ids = set()
    duplicate_ids = set()

    # CHECK 2: Validate metadata and compare each clause
    # against the canonical clause in the policy corpus.
    for clause in clauses:
        if not isinstance(clause, dict):
            errors.append("Retrieved clause is not a valid dictionary")
            continue

        clause_id = clause.get("clause_id")
        text = clause.get("text")
        page = clause.get("page")
        section = clause.get("section")

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

        if not isinstance(section, str) or not section.strip():
            errors.append(
                f"Clause {clause_id} is missing its section"
            )

        # CHECK 3: Confirm that the clause actually exists
        # in the canonical policy corpus.
        canonical_clause = lookup_clause(clause_id)

        if canonical_clause is None:
            errors.append(
                f"Unsupported clause citation: {clause_id}"
            )
            continue

        # CHECK 4: Confirm that citation details have not
        # been changed or fabricated.
        if text != canonical_clause.get("text"):
            errors.append(
                f"Clause {clause_id} text does not match the policy corpus"
            )

        if page != canonical_clause.get("page"):
            errors.append(
                f"Clause {clause_id} page does not match the policy corpus"
            )

        if section != canonical_clause.get("section"):
            errors.append(
                f"Clause {clause_id} section does not match the policy corpus"
            )

    # CHECK 5: Detect duplicate clause identifiers.
    for clause_id in sorted(duplicate_ids):
        errors.append(
            f"Duplicate clause identifier: {clause_id}"
        )

    # CHECK 6: Identify sections found in retrieved clauses.
    found_sections = {
        clause["section"].strip().lower()
        for clause in clauses
        if isinstance(clause, dict)
        and isinstance(clause.get("section"), str)
        and clause["section"].strip()
    }

    missing_sections = REQUIRED_SECTIONS - found_sections

    for section in sorted(missing_sections):
        errors.append(
            f"Missing supporting provision: {section}"
        )

    # CHECK 7: Check unresolved investigation items.
    if investigation.unresolved_checks:
        errors.extend(investigation.unresolved_checks)

    # CHECK 8: Extract procedure from investigation notes.
    # Support both the old and current note formats.
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

    # CHECK 9: Check basic relevance of coverage evidence.
    coverage_clauses = [
        clause
        for clause in clauses
        if isinstance(clause, dict)
        and isinstance(clause.get("section"), str)
        and clause["section"].strip().lower() == "coverage"
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

    else:
        errors.append(
            "Procedure information is missing from investigation notes"
        )

    # CHECK 10: Collect only citations that passed all checks.
    verified_clause_ids = []

    for clause in clauses:
        if not isinstance(clause, dict):
            continue

        clause_id = clause.get("clause_id")

        if not isinstance(clause_id, str):
            continue

        clause_id = clause_id.strip()

        canonical_clause = lookup_clause(clause_id)

        if canonical_clause is None:
            continue

        citation_matches = (
            clause.get("text") == canonical_clause.get("text")
            and clause.get("page") == canonical_clause.get("page")
            and clause.get("section") == canonical_clause.get("section")
            and isinstance(clause.get("text"), str)
            and bool(clause.get("text").strip())
            and isinstance(clause.get("page"), int)
            and not isinstance(clause.get("page"), bool)
            and clause.get("page") > 0
            and isinstance(clause.get("section"), str)
            and bool(clause.get("section").strip())
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
