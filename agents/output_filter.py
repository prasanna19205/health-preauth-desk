
from agents.schemas import (
    AgentResult,
    CoverageRecommendation,
)


def filter_agent_output(
    recommendation: AgentResult,
    verification: dict,
) -> dict:
    """
    Validates the final agent recommendation before it
    is returned to the caller.

    Checks:
    1. Recommendation has a valid decision.
    2. Every supporting clause is verified.
    3. The agent does not claim final admission authorisation.
    4. Invalid output is escalated for human review.
    """

    errors = []

    # Check 1: Verify recommendation type
    if not isinstance(recommendation, AgentResult):
        errors.append("Invalid recommendation object.")

    else:
        if not isinstance(
            recommendation.recommendation,
            CoverageRecommendation,
        ):
            errors.append("Invalid recommendation decision.")

        # Check 2: Prevent claims of final authorisation
        unsafe_phrases = [
            "admission is authorised",
            "admission is approved",
            "final approval granted",
            "patient can be admitted",
            "guaranteed coverage",
        ]

        reason = recommendation.reason.lower()

        for phrase in unsafe_phrases:
            if phrase in reason:
                errors.append(
                    "Output contains an unauthorised final approval claim."
                )
                break

    # Check 3: Verify supporting clause IDs
    verified_ids = set(
        verification.get("verified_clause_ids", [])
    )

    if not verification.get("verified", False):
        errors.append("Evidence verification did not pass.")

    if isinstance(recommendation, AgentResult):
        for clause_id in recommendation.supporting_clauses:
            if clause_id not in verified_ids:
                errors.append(
                    f"Unsupported clause citation: {clause_id}"
                )

    # Return filtered result
    if errors:
        return {
            "safe": False,
            "errors": errors,
            "recommendation": CoverageRecommendation.MEDICAL_REVIEW,
            "message": (
                "Output failed safety validation. "
                "Human medical officer review is required."
            ),
        }

    return {
        "safe": True,
        "errors": [],
        "recommendation": recommendation.recommendation,
        "message": recommendation.reason,
    }
