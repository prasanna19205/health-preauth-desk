
from datetime import date

from agents.schemas import (
    PreAuthRequest,
    RequestAnalysis,
    PreExistingStatus,
)


def calculate_policy_age_months(
    start_date: date,
    admission_date: date
) -> int:
    """Calculate completed months between two dates."""

    months = (
        (admission_date.year - start_date.year) * 12
        + admission_date.month
        - start_date.month
    )

    if admission_date.day < start_date.day:
        months -= 1

    return max(0, months)


def analyze_request(
    request: PreAuthRequest
) -> RequestAnalysis:
    """
    Agent 1:
    Classifies the admission and extracts information
    needed by the coverage investigation agent.
    """

    policy_age = calculate_policy_age_months(
        request.policy_start_date,
        request.admission_date
    )

    investigation_checks = [
        "Verify whether the insurance policy is active",
        "Check the coverage clause for the procedure",
        "Check applicable waiting periods",
        "Check permanent exclusions",
        "Check procedure-specific sub-limits",
        "Check room category eligibility",
    ]

    missing_information = []
    escalation_flags = []

    if request.pre_existing_condition == PreExistingStatus.UNKNOWN:
        escalation_flags.append(
            "Pre-existing condition status is unknown"
        )

    if not request.diagnosis:
        missing_information.append(
            "Diagnosis details are not provided"
        )

    if request.pre_existing_condition == PreExistingStatus.YES:
        escalation_flags.append(
            "Possible pre-existing condition requires review"
        )

    return RequestAnalysis(
        admission_type=request.admission_type,
        procedure=request.procedure,
        policy_age_months=policy_age,
        investigation_checks=investigation_checks,
        missing_information=missing_information,
        escalation_flags=escalation_flags,
    )
