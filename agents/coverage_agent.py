
from agents.schemas import (
    PreAuthRequest,
    RequestAnalysis,
    CoverageInvestigation,
)
from agents.tools import (
    search_policy,
    lookup_clause,
    lookup_request_field,
)


def investigate_coverage(
    request: PreAuthRequest,
    analysis: RequestAnalysis,
    retry: bool = False,
) -> CoverageInvestigation:
    """
    Investigate policy coverage by retrieving supporting clauses.

    First attempt:
        Uses procedure-specific searches.

    Retry:
        Uses an alternative broad-section retrieval strategy.
    """

    # Retrieve important request fields.
    procedure = lookup_request_field(request, "procedure")
    room_category = lookup_request_field(request, "room_category")
    admission_date = lookup_request_field(request, "admission_date")

    procedure_lower = procedure.lower()
    room_category_lower = room_category.lower()

    checks_performed = [
        f"Identified procedure: {procedure}",
        f"Identified room category: {room_category}",
        f"Identified admission date: {admission_date}",
    ]

    # Choose retrieval strategy.
    if not retry:
        strategy_name = "Procedure-specific retrieval strategy"

        queries = [
            procedure_lower,
            f"{procedure_lower} waiting period",
            f"{procedure_lower} exclusions",
            f"{procedure_lower} sub-limits",
            f"{room_category_lower} room category eligibility",
        ]

    else:
        strategy_name = "Alternative broad-section retrieval strategy"

        queries = [
            "coverage conditions and limitations",
            "waiting period from policy commencement",
            "permanent exclusions",
            "procedure financial sub-limits",
            "room eligibility and policy schedule",
        ]

    # Retrieve clauses.
    retrieved_clauses = []
    retrieved_clause_ids = set()

    for query in queries:
        search_results = search_policy(query)

        checks_performed.append(
            f"Executed policy search: {query}"
        )

        for result in search_results:
            clause_id = result.get("clause_id")

            if not clause_id:
                continue

            if clause_id in retrieved_clause_ids:
                continue

            clause = lookup_clause(clause_id)

            if clause is None:
                continue

            retrieved_clauses.append(clause)
            retrieved_clause_ids.add(clause_id)

    # Identify required policy sections.
    required_sections = {
        "coverage",
        "waiting period",
        "exclusions",
        "sub-limits",
        "room eligibility",
    }

    sections_found = {
        clause.get("section", "").strip().lower()
        for clause in retrieved_clauses
    }

    unresolved_checks = []

    for section in required_sections:
        if section not in sections_found:
            unresolved_checks.append(
                f"No supporting clause found for {section}"
            )

    # Record investigation details and selected strategy.
    investigation_notes = [
        f"Policy age: {analysis.policy_age_months} months",
        f"Procedure investigated: {procedure}",
        f"Room category investigated: {room_category}",
        f"Admission date: {admission_date}",
        f"Retrieval strategy: {strategy_name}",
        f"Unique clauses retrieved: {len(retrieved_clauses)}",
    ]

    return CoverageInvestigation(
        retrieved_clauses=retrieved_clauses,
        checks_performed=checks_performed,
        unresolved_checks=unresolved_checks,
        investigation_notes=investigation_notes,
    )
