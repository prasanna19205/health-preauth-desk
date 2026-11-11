
import re

from agents.schemas import (
    PreAuthRequest,
    RequestAnalysis,
    CoverageInvestigation,
    AgentResult,
    CoverageRecommendation,
)


def normalize_text(value: str) -> str:
    """Normalize text for reliable word-level comparisons."""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def procedure_is_relevant(procedure: str, clause_text: str) -> bool:
    """
    Check whether a clause refers to the requested procedure.

    Common words such as 'surgery' and 'procedure' are ignored.
    All remaining meaningful procedure words must appear
    in the clause to establish relevance.
    """

    stopwords = {
        "surgery",
        "procedure",
        "procedures",
        "operation",
        "operations",
        "treatment",
        "medical",
        "the",
        "and",
        "of",
        "for",
        "under",
    }

    procedure_words = {
        word
        for word in normalize_text(procedure).split()
        if len(word) > 2 and word not in stopwords
    }

    clause_words = set(normalize_text(clause_text).split())

    if not procedure_words:
        return False

    return procedure_words.issubset(clause_words)


def extract_waiting_months(clause_text: str):
    """
    Extract a waiting period expressed in months.

    Supports:
    - waiting period of 24 months
    - 24-month waiting period
    - waiting period: 24 months
    - waiting period - 24 months
    """

    patterns = [
        r"waiting period of\s+(\d+)\s+months?",
        r"(\d+)\s*-\s*months?\s+waiting period",
        r"waiting period\s*[:\-]?\s*(\d+)\s+months?",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            clause_text,
            re.IGNORECASE,
        )

        if match:
            return int(match.group(1))

    return None


def make_recommendation(
    request: PreAuthRequest,
    analysis: RequestAnalysis,
    investigation: CoverageInvestigation,
    verification: dict,
) -> AgentResult:
    """
    Produce a conservative pre-authorisation recommendation.

    The system only recommends a route.
    It never makes the final admission decision.
    """

    clauses = investigation.retrieved_clauses

    # Use only clause IDs accepted by the verification agent.
    verified_ids = set(
        verification.get("verified_clause_ids", [])
    )

    supporting_clause_ids = sorted(verified_ids)

    # 1. Evidence must pass verification.
    if not verification.get("verified", False):
        return AgentResult(
            recommendation=CoverageRecommendation.MEDICAL_REVIEW,
            reason="Policy evidence could not be fully verified.",
            supporting_clauses=[],
            missing_information=investigation.unresolved_checks,
            requires_human_review=True,
        )

    # 2. Pre-existing conditions and escalation flags.
    if analysis.escalation_flags:
        return AgentResult(
            recommendation=CoverageRecommendation.MEDICAL_REVIEW,
            reason=(
                "A pre-existing condition or another escalation "
                "flag requires medical officer review."
            ),
            supporting_clauses=supporting_clause_ids,
            missing_information=[],
            requires_human_review=True,
        )

    # 3. Missing request information.
    if analysis.missing_information:
        return AgentResult(
            recommendation=CoverageRecommendation.QUERY_TO_HOSPITAL,
            reason=(
                "Additional information is required to assess coverage."
            ),
            supporting_clauses=supporting_clause_ids,
            missing_information=analysis.missing_information,
            requires_human_review=False,
        )

    # 4. Find coverage clauses.
    coverage_clauses = [
        clause
        for clause in clauses
        if isinstance(clause.get("section"), str)
        and clause["section"].strip().lower() == "coverage"
    ]

    relevant_coverage_clauses = [
        clause
        for clause in coverage_clauses
        if isinstance(clause.get("text"), str)
        and procedure_is_relevant(
            request.procedure,
            clause["text"],
        )
    ]

    if not relevant_coverage_clauses:
        return AgentResult(
            recommendation=CoverageRecommendation.MEDICAL_REVIEW,
            reason=(
                f"No relevant coverage provision was found for "
                f"the procedure: {request.procedure}. "
                "Medical officer review is required."
            ),
            supporting_clauses=supporting_clause_ids,
            missing_information=[],
            requires_human_review=True,
        )

    # 5. Find exclusion clauses relevant to this procedure.
    exclusion_clauses = [
        clause
        for clause in clauses
        if isinstance(clause.get("section"), str)
        and clause["section"].strip().lower() == "exclusions"
    ]

    relevant_exclusions = []

    for clause in exclusion_clauses:
        clause_text = clause.get("text", "")

        if not isinstance(clause_text, str):
            continue

        if not procedure_is_relevant(
            request.procedure,
            clause_text,
        ):
            continue

        explicit_exclusion = re.search(
            r"\b(excluded|not covered|non[- ]covered)\b",
            clause_text,
            re.IGNORECASE,
        )

        if explicit_exclusion:
            relevant_exclusions.append(clause)

    # 6. Check for conflicting coverage and exclusion evidence.
    # This check must happen before the exclusion-only decision.
    for coverage_clause in relevant_coverage_clauses:
        coverage_text = coverage_clause.get("text", "")

        if not isinstance(coverage_text, str):
            continue

        positive_coverage = re.search(
            r"\bcovered under (?:the )?policy\b"
            r"|\b(?:is|are) covered\b",
            coverage_text,
            re.IGNORECASE,
        )

        if not positive_coverage:
            continue

        for exclusion_clause in relevant_exclusions:
            supporting_ids = [
                clause_id
                for clause_id in [
                    coverage_clause.get("clause_id"),
                    exclusion_clause.get("clause_id"),
                ]
                if clause_id in verified_ids
            ]

            return AgentResult(
                recommendation=CoverageRecommendation.MEDICAL_REVIEW,
                reason=(
                    "Potentially conflicting coverage and exclusion "
                    "evidence was retrieved for the procedure. "
                    "Medical officer review is required."
                ),
                supporting_clauses=supporting_ids,
                missing_information=[],
                requires_human_review=True,
            )

    # 7. An applicable exclusion without conflicting coverage
    # still requires medical officer review.
    if relevant_exclusions:
        clause = relevant_exclusions[0]

        clause_id = clause.get("clause_id")

        return AgentResult(
            recommendation=CoverageRecommendation.MEDICAL_REVIEW,
            reason=(
                f"Retrieved exclusion wording appears to apply "
                f"to {request.procedure}. Medical officer review "
                "is required before a coverage position can be made."
            ),
            supporting_clauses=(
                [clause_id] if clause_id in verified_ids else []
            ),
            missing_information=[],
            requires_human_review=True,
        )

    # 8. Check applicable waiting periods.
    waiting_clauses = [
        clause
        for clause in clauses
        if isinstance(clause.get("section"), str)
        and clause["section"].strip().lower() == "waiting period"
    ]

    for clause in waiting_clauses:
        clause_text = clause.get("text", "")

        if not isinstance(clause_text, str):
            continue

        # Apply only a waiting period relevant to the procedure.
        if not procedure_is_relevant(
            request.procedure,
            clause_text,
        ):
            continue

        waiting_months = extract_waiting_months(clause_text)

        if waiting_months is None:
            clause_id = clause.get("clause_id")

            return AgentResult(
                recommendation=CoverageRecommendation.MEDICAL_REVIEW,
                reason=(
                    "A potentially applicable waiting period was found, "
                    "but its duration could not be reliably extracted."
                ),
                supporting_clauses=(
                    [clause_id] if clause_id in verified_ids else []
                ),
                missing_information=[],
                requires_human_review=True,
            )

        if analysis.policy_age_months < waiting_months:
            clause_id = clause.get("clause_id")

            return AgentResult(
                recommendation=CoverageRecommendation.MEDICAL_REVIEW,
                reason=(
                    f"The policy age is {analysis.policy_age_months} "
                    f"months, which is shorter than the "
                    f"{waiting_months}-month waiting period "
                    "found in the retrieved clause."
                ),
                supporting_clauses=(
                    [clause_id] if clause_id in verified_ids else []
                ),
                missing_information=[],
                requires_human_review=True,
            )

    # 9. Do not recommend approval if checks remain unresolved.
    if investigation.unresolved_checks:
        return AgentResult(
            recommendation=CoverageRecommendation.MEDICAL_REVIEW,
            reason=(
                "Some required policy provisions remain unresolved."
            ),
            supporting_clauses=supporting_clause_ids,
            missing_information=investigation.unresolved_checks,
            requires_human_review=True,
        )

    # 10. All implemented checks passed.
    return AgentResult(
        recommendation=CoverageRecommendation.APPROVE_RECOMMENDED,
        reason=(
            "The retrieved evidence passed verification and no "
            "blocking condition was identified. Final admission "
            "approval remains with the medical officer."
        ),
        supporting_clauses=supporting_clause_ids,
        missing_information=[],
        requires_human_review=False,
    )
