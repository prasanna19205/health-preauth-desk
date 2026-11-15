
from agents.schemas import (
    PreAuthRequest,
    RequestAnalysis,
    CoverageInvestigation,
)

from agents.tools import (
    lookup_request_field,
    search_policy,
    lookup_clause_parts,
    search_policy_modifiers,
    check_policy_waiting_period,
    check_procedure_daycare,
)


def investigate_coverage(
    request: PreAuthRequest,
    analysis: RequestAnalysis,
    retry: bool = False,
) -> CoverageInvestigation:
    """
    Investigate policy coverage using the real RAG corpus.

    First attempt:
        Procedure-specific retrieval.

    Retry:
        Alternative broad-section retrieval.

    Important:
        Missing evidence is not treated as proof of exclusion.
        Unresolved checks are explicitly recorded for escalation.
    """

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

    if not retry:
        strategy_name = "Procedure-specific retrieval strategy"

        coverage_queries = [
            procedure_lower,
            f"{procedure_lower} coverage conditions",
        ]

        modifier_query = (
            f"{procedure_lower} waiting period exclusions "
            f"sub-limits limitations"
        )

    else:
        strategy_name = "Alternative broad-section retrieval strategy"

        coverage_queries = [
            f"{procedure_lower} policy coverage and conditions",
            "covered medical treatments and procedures",
        ]

        modifier_query = (
            f"policy waiting periods permanent exclusions "
            f"financial sub-limits for {procedure_lower}"
        )

    retrieved_clauses = []
    retrieved_clause_ids = set()

    def add_clause(clause):
        """Add a clause only once, using its exact RAG identifier."""

        if not isinstance(clause, dict):
            return

        clause_id = clause.get("clause_id")

        if not isinstance(clause_id, str) or not clause_id:
            return

        if clause_id not in retrieved_clause_ids:
            retrieved_clauses.append(clause)
            retrieved_clause_ids.add(clause_id)

    # -----------------------------------------------------
    # 1. Retrieve coverage provisions
    # -----------------------------------------------------

    for query in coverage_queries:
        results = search_policy(
            query,
            section_type="cover",
            k=5,
        )

        checks_performed.append(
            f"Coverage search executed: {query}"
        )

        for result in results:
            clause_id = result.get("clause_id")

            if clause_id:
                parts = lookup_clause_parts(clause_id)

                if parts:
                    for part in parts:
                        add_clause(part)
                else:
                    add_clause(result)

    # -----------------------------------------------------
    # 2. Retrieve waiting-period provisions
    # -----------------------------------------------------

    waiting_result = check_policy_waiting_period(procedure)

    checks_performed.append(
        f"Waiting-period check performed for: {procedure}"
    )

    waiting_matches = waiting_result.get("matches", [])

    for clause in waiting_matches:
        clause_id = clause.get("clause_id")

        if clause_id:
            parts = lookup_clause_parts(clause_id)

            if parts:
                for part in parts:
                    add_clause(part)
            else:
                add_clause(clause)

    if not waiting_result.get("listed"):
        checks_performed.append(
            "No matching waiting-period provision was found"
        )

    # -----------------------------------------------------
    # 3. Retrieve exclusions and sub-limits
    # -----------------------------------------------------

    modifier_results = search_policy_modifiers(
        modifier_query,
        k=3,
    )

    checks_performed.append(
        "Searched waiting-period, exclusion and sub-limit provisions"
    )

    for result in modifier_results:
        clause_id = result.get("clause_id")

        if clause_id:
            parts = lookup_clause_parts(clause_id)

            if parts:
                for part in parts:
                    add_clause(part)
            else:
                add_clause(result)

    # -----------------------------------------------------
    # 4. Check day-care procedure listing
    # -----------------------------------------------------

    daycare_result = check_procedure_daycare(procedure)

    checks_performed.append(
        f"Day-care list check: {daycare_result.get('status')}"
    )

    for clause in daycare_result.get("matches", []):
        add_clause(clause)

    # -----------------------------------------------------
    # 5. Record unresolved checks
    # -----------------------------------------------------

    unresolved_checks = []

    coverage_found = any(
        clause.get("section_type") == "cover"
        for clause in retrieved_clauses
    )

    if not coverage_found:
        unresolved_checks.append(
            "No relevant coverage provision was retrieved"
        )

    if (
        daycare_result.get("status") == "not_found"
        and analysis.admission_type.value == "day_care"
    ):
        unresolved_checks.append(
            "Day-care procedure was not found in the indexed list; "
            "this does not establish exclusion"
        )

    # Room eligibility needs an actual policy schedule check.
    # Do not invent a room limit if the evidence is unavailable.
    checks_performed.append(
        f"Room category recorded for policy review: {room_category}"
    )

    # -----------------------------------------------------
    # 6. Record investigation details
    # -----------------------------------------------------

    investigation_notes = [
        f"Policy age: {analysis.policy_age_months} months",
        f"Procedure investigated: {procedure}",
        f"Room category investigated: {room_category}",
        f"Admission date: {admission_date}",
        f"Retrieval strategy: {strategy_name}",
        f"Waiting-period match: {waiting_result.get('listed')}",
        f"Day-care status: {daycare_result.get('status')}",
        f"Unique clauses retrieved: {len(retrieved_clauses)}",
    ]

    return CoverageInvestigation(
        retrieved_clauses=retrieved_clauses,
        checks_performed=checks_performed,
        unresolved_checks=unresolved_checks,
        investigation_notes=investigation_notes,
    )
