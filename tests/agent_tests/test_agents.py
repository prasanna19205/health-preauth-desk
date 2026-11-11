
from datetime import date
from decimal import Decimal

import pytest

from agents.schemas import (
    PreAuthRequest,
    AdmissionType,
    PreExistingStatus,
)
from agents.request_agent import analyze_request
from agents.coverage_agent import investigate_coverage
from agents.tools import (
    search_policy,
    lookup_clause,
    lookup_request_field,
)


def create_test_request():
    """Create a sample pre-authorisation request for testing."""
    return PreAuthRequest(
        patient_id="P001",
        policy_id="POL001",
        policy_start_date=date(2025, 12, 1),
        admission_date=date(2026, 11, 10),
        procedure="Cataract Surgery",
        admission_type=AdmissionType.PLANNED_SURGICAL,
        room_category="Standard",
        estimated_cost=Decimal("50000"),
        diagnosis="Cataract",
        pre_existing_condition=PreExistingStatus.NO,
    )


# --------------------------------------------------
# REQUEST ANALYSIS AGENT TEST
# --------------------------------------------------

def test_request_analysis_agent():
    """Check whether Agent 1 correctly analyses the request."""

    request = create_test_request()
    analysis = analyze_request(request)

    assert analysis.procedure == "Cataract Surgery"
    assert analysis.policy_age_months == 11

    assert any(
        "waiting periods" in check.lower()
        for check in analysis.investigation_checks
    )

    assert analysis.missing_information == []


# --------------------------------------------------
# COVERAGE INVESTIGATION AGENT TESTS
# --------------------------------------------------

def test_coverage_investigation_agent():
    """Check whether Agent 2 retrieves policy clauses."""

    request = create_test_request()
    analysis = analyze_request(request)

    investigation = investigate_coverage(request, analysis)

    assert len(investigation.retrieved_clauses) > 0
    assert len(investigation.checks_performed) > 0
    assert investigation.unresolved_checks == []


def test_coverage_agent_retry_strategy():
    """Check whether Agent 2 uses a different strategy on retry."""

    request = create_test_request()
    analysis = analyze_request(request)

    first_attempt = investigate_coverage(
        request, analysis, retry=False
    )

    retry_attempt = investigate_coverage(
        request, analysis, retry=True
    )

    assert any(
        "procedure-specific" in note.lower()
        for note in first_attempt.investigation_notes
    )

    assert any(
        "alternative broad-section" in note.lower()
        for note in retry_attempt.investigation_notes
    )


# --------------------------------------------------
# TOOL 1: SEARCH POLICY TESTS
# --------------------------------------------------

def test_search_policy_finds_cataract_clause():
    """Check whether policy search finds cataract coverage."""

    results = search_policy("cataract surgery")

    assert len(results) > 0

    assert any(
        clause["clause_id"] == "COV-001"
        for clause in results
    )


def test_search_policy_returns_empty_for_unknown_topic():
    """Check behaviour when no matching clause exists."""

    results = search_policy("underwater photography")

    assert results == []


# --------------------------------------------------
# TOOL 2: LOOKUP CLAUSE TESTS
# --------------------------------------------------

def test_lookup_clause_by_id():
    """Check whether a clause can be retrieved using its ID."""

    clause = lookup_clause("COV-001")

    assert clause is not None
    assert clause["clause_id"] == "COV-001"
    assert clause["section"] == "Coverage"


def test_lookup_invalid_clause_id():
    """Check behaviour when an invalid clause ID is provided."""

    clause = lookup_clause("INVALID-999")

    assert clause is None


# --------------------------------------------------
# TOOL 3: LOOKUP REQUEST FIELD TESTS
# --------------------------------------------------

def test_lookup_request_field():
    """Check whether a request field can be retrieved."""

    request = create_test_request()

    procedure = lookup_request_field(
        request, "procedure"
    )

    assert procedure == "Cataract Surgery"


def test_lookup_invalid_request_field():
    """Check whether invalid request fields are rejected."""

    request = create_test_request()

    with pytest.raises(ValueError):
        lookup_request_field(
            request, "invalid_field"
        )
