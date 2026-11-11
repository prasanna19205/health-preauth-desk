
from agents.output_filter import filter_agent_output

from agents.schemas import (
    AgentResult,
    CoverageRecommendation,
)


def create_valid_recommendation():
    return AgentResult(
        recommendation=CoverageRecommendation.APPROVE_RECOMMENDED,
        reason="The retrieved policy evidence supports this recommendation.",
        supporting_clauses=["COV-001", "WAIT-001"],
        missing_information=[],
        requires_human_review=False,
    )


def create_valid_verification():
    return {
        "verified": True,
        "verified_clause_ids": ["COV-001", "WAIT-001"],
    }


def test_valid_output_passes_filter():
    result = filter_agent_output(
        create_valid_recommendation(),
        create_valid_verification(),
    )

    assert result["safe"] is True
    assert result["recommendation"] == CoverageRecommendation.APPROVE_RECOMMENDED


def test_unverified_citation_is_rejected():
    recommendation = create_valid_recommendation()
    recommendation.supporting_clauses.append("UNKNOWN-999")

    result = filter_agent_output(
        recommendation,
        create_valid_verification(),
    )

    assert result["safe"] is False
    assert result["recommendation"] == CoverageRecommendation.MEDICAL_REVIEW


def test_failed_verification_is_rejected():
    result = filter_agent_output(
        create_valid_recommendation(),
        {
            "verified": False,
            "verified_clause_ids": [],
        },
    )

    assert result["safe"] is False


def test_final_admission_authorisation_claim_is_rejected():
    recommendation = create_valid_recommendation()
    recommendation.reason = "Admission is authorised."

    result = filter_agent_output(
        recommendation,
        create_valid_verification(),
    )

    assert result["safe"] is False
    assert result["recommendation"] == CoverageRecommendation.MEDICAL_REVIEW


def test_invalid_recommendation_object_is_rejected():
    result = filter_agent_output(
        "Approve this admission",
        create_valid_verification(),
    )

    assert result["safe"] is False
    assert result["recommendation"] == CoverageRecommendation.MEDICAL_REVIEW
