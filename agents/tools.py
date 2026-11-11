
"""
Mock policy retrieval tools.

These tools will initially use sample policy clauses.
Later, Person 1's actual RAG retrieval functions
will replace the mock implementation.
"""

from agents.schemas import PreAuthRequest


# Synthetic policy clauses for development and testing.
# These are NOT real insurance policy provisions.

MOCK_POLICY_CLAUSES = [
    {
        "clause_id": "COV-001",
        "section": "Coverage",
        "topic": "cataract surgery",
        "text": (
            "Cataract surgery is covered under the policy, "
            "subject to applicable waiting periods, exclusions "
            "and sub-limits."
        ),
        "page": 12,
    },
    {
        "clause_id": "WAIT-001",
        "section": "Waiting Period",
        "topic": "cataract waiting period",
        "text": (
            "Illustrative rule: Cataract surgery is subject "
            "to a waiting period of 24 months from the "
            "policy commencement date."
        ),
        "page": 28,
    },
    {
        "clause_id": "COV-002",
        "section": "Coverage",
        "topic": "knee replacement",
        "text": (
            "Knee replacement surgery is covered under the policy."
        ),
        "page": 30,
    },
    {
        "clause_id": "EXC-002",
        "section": "Exclusions",
        "topic": "knee replacement",
        "text": (
            "Knee replacement surgery is explicitly excluded "
            "and is not covered under the policy."
        ),
        "page": 36,
    },
    {
        "clause_id": "EXC-001",
        "section": "Exclusions",
        "topic": "permanent exclusions",
        "text": (
            "Procedures explicitly listed under permanent "
            "exclusions are not covered under the policy."
        ),
        "page": 35,
    },
    {
        "clause_id": "LIMIT-001",
        "section": "Sub-limits",
        "topic": "procedure sub-limit",
        "text": (
            "Certain medical procedures may have specific "
            "financial sub-limits as stated in the policy."
        ),
        "page": 41,
    },
    {
        "clause_id": "ROOM-001",
        "section": "Room Eligibility",
        "topic": "room category",
        "text": (
            "Room category eligibility and applicable "
            "limits must be checked against the policy schedule."
        ),
        "page": 19,
    },
]


def search_policy(query: str) -> list[dict]:
    """
    Search mock policy clauses using procedure/topic relevance
    and section keywords.
    """

    query_words = set(query.lower().split())

    results = []

    for clause in MOCK_POLICY_CLAUSES:
        topic_words = set(clause["topic"].lower().split())
        section_words = set(clause["section"].lower().split())

        # Match a clause when its complete topic appears
        # in the search query.
        topic_match = (
            bool(topic_words)
            and topic_words.issubset(query_words)
        )

        # Allow searches for complete section names.
        section_match = (
            bool(section_words)
            and section_words.issubset(query_words)
        )

        if topic_match or section_match:
            results.append(clause)

    return results


def lookup_clause(clause_id: str) -> dict | None:
    """
    Retrieve a specific clause using its ID.
    """

    for clause in MOCK_POLICY_CLAUSES:
        if clause["clause_id"] == clause_id:
            return clause

    return None


def lookup_request_field(
    request: PreAuthRequest,
    field_name: str
):
    """
    Retrieve a specific field from the hospital request.
    """

    if field_name not in PreAuthRequest.model_fields:
        raise ValueError(
            f"Unknown request field: {field_name}"
        )

    return getattr(request, field_name)
