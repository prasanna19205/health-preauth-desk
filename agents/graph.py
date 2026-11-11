
from typing import TypedDict, Optional
from time import perf_counter
from functools import wraps

from langgraph.graph import StateGraph, START, END

from agents.schemas import (
    PreAuthRequest,
    RequestAnalysis,
    CoverageInvestigation,
    AgentResult,
    CoverageRecommendation,
)

from agents.metrics import agent_metrics
from agents.security import check_request_for_injection
from agents.request_agent import analyze_request
from agents.coverage_agent import investigate_coverage
from agents.verification import verify_investigation
from agents.decision_agent import make_recommendation
from agents.output_filter import filter_agent_output


# Track execution time and success/failure for each agent
def track_agent(agent_name):
    def decorator(func):
        @wraps(func)
        def wrapper(state):
            start_time = perf_counter()
            success = False

            try:
                result = func(state)
                success = True
                return result

            finally:
                duration = perf_counter() - start_time

                agent_metrics.record(
                    agent_name,
                    duration,
                    success,
                )

        return wrapper
    return decorator


# Shared information passed between agents
class AgentState(TypedDict):
    request: PreAuthRequest
    security_check: Optional[dict]
    analysis: Optional[RequestAnalysis]
    investigation: Optional[CoverageInvestigation]
    verification: Optional[dict]
    recommendation: Optional[AgentResult]
    output_filter_result: Optional[dict]
    attempts: int
    max_attempts: int
    status: str


# SECURITY CHECK
@track_agent("security_check")
def security_check_node(state: AgentState):
    print("\n--- SECURITY CHECK ---")

    result = check_request_for_injection(state["request"])

    print("Suspicious input detected:", result["is_suspicious"])

    if result["is_suspicious"]:
        print("Security findings:", result["findings"])

    return {
        "security_check": result,
        "status": (
            "security_review_required"
            if result["is_suspicious"]
            else "security_check_passed"
        ),
    }


def route_after_security_check(state: AgentState):
    if state["security_check"]["is_suspicious"]:
        return "block"

    return "continue"


# AGENT 1: Request analysis
@track_agent("request_analysis")
def request_analysis_node(state: AgentState):
    print("\n--- AGENT 1: REQUEST ANALYSIS ---")

    analysis = analyze_request(state["request"])

    print("Procedure:", analysis.procedure)
    print("Policy age:", analysis.policy_age_months, "months")

    return {
        "analysis": analysis,
        "status": "request_analysed",
    }


# AGENT 2: Coverage investigation
@track_agent("coverage_investigation")
def coverage_investigation_node(state: AgentState):
    print("\n--- AGENT 2: COVERAGE INVESTIGATION ---")

    is_retry = state["attempts"] > 0

    investigation = investigate_coverage(
        state["request"],
        state["analysis"],
        retry=is_retry,
    )

    print("Retry strategy:", is_retry)
    print("Clauses retrieved:", len(investigation.retrieved_clauses))

    return {
        "investigation": investigation,
        "attempts": state["attempts"] + 1,
        "status": "investigation_completed",
    }


# Evidence verification
@track_agent("verification")
def verification_node(state: AgentState):
    print("\n--- EVIDENCE VERIFICATION ---")

    result = verify_investigation(
        state["investigation"]
    )

    print("Verified:", result["verified"])

    return {
        "verification": result,
        "status": (
            "verified"
            if result["verified"]
            else "verification_failed"
        ),
    }


def route_after_verification(state: AgentState):
    if state["verification"]["verified"]:
        return "complete"

    if state["attempts"] < state["max_attempts"]:
        return "retry"

    return "escalate"


# Retry investigation
def retry_node(state: AgentState):
    print("\n--- RETRIEVAL RETRY ---")
    print("Switching to alternative retrieval strategy.")

    return {
        "status": "retrying_investigation",
    }


# Escalation
def escalation_node(state: AgentState):
    if (
        state.get("security_check")
        and state["security_check"]["is_suspicious"]
    ):
        print("\n--- SECURITY REVIEW REQUIRED ---")
        print("Suspicious instructions detected in request.")
    else:
        print("\n--- HUMAN REVIEW REQUIRED ---")

    return {
        "status": "medical-review",
    }


# DECISION AGENT
@track_agent("decision")
def decision_node(state: AgentState):
    print("\n--- DECISION AGENT ---")

    recommendation = make_recommendation(
        state["request"],
        state["analysis"],
        state["investigation"],
        state["verification"],
    )

    print(
        "Recommendation:",
        recommendation.recommendation.value,
    )

    print("Reason:", recommendation.reason)

    return {
        "recommendation": recommendation,
        "status": recommendation.recommendation.value,
    }


# OUTPUT SAFETY FILTER
@track_agent("output_filter")
def output_filter_node(state: AgentState):
    print("\n--- OUTPUT SAFETY FILTER ---")

    recommendation = state["recommendation"]
    verification = state["verification"]

    result = filter_agent_output(
        recommendation,
        verification,
    )

    print("Output safe:", result["safe"])

    if not result["safe"]:
        print("Output filter errors:", result["errors"])

        safe_recommendation = AgentResult(
            recommendation=CoverageRecommendation.MEDICAL_REVIEW,
            reason=result["message"],
            supporting_clauses=[],
            missing_information=result["errors"],
            requires_human_review=True,
        )

        return {
            "recommendation": safe_recommendation,
            "output_filter_result": result,
            "status": "medical-review",
        }

    return {
        "output_filter_result": result,
        "status": recommendation.recommendation.value,
    }


# Build the LangGraph workflow
workflow = StateGraph(AgentState)

workflow.add_node("security_check", security_check_node)
workflow.add_node("request_analysis", request_analysis_node)
workflow.add_node("coverage_investigation", coverage_investigation_node)
workflow.add_node("verification", verification_node)
workflow.add_node("retry", retry_node)
workflow.add_node("escalation", escalation_node)
workflow.add_node("decision", decision_node)
workflow.add_node("output_filter", output_filter_node)


# Define agent hand-offs
workflow.add_edge(START, "security_check")

workflow.add_conditional_edges(
    "security_check",
    route_after_security_check,
    {
        "continue": "request_analysis",
        "block": "escalation",
    },
)

workflow.add_edge("request_analysis", "coverage_investigation")
workflow.add_edge("coverage_investigation", "verification")

workflow.add_conditional_edges(
    "verification",
    route_after_verification,
    {
        "complete": "decision",
        "retry": "retry",
        "escalate": "escalation",
    },
)

workflow.add_edge("retry", "coverage_investigation")
workflow.add_edge("decision", "output_filter")
workflow.add_edge("output_filter", END)
workflow.add_edge("escalation", END)


# Compile workflow
agent_graph = workflow.compile()


def run_agent_workflow(
    request: PreAuthRequest,
    max_attempts: int = 2,
):
    """Execute the complete multi-agent workflow."""

    initial_state = {
        "request": request,
        "security_check": None,
        "analysis": None,
        "investigation": None,
        "verification": None,
        "recommendation": None,
        "output_filter_result": None,
        "attempts": 0,
        "max_attempts": max_attempts,
        "status": "started",
    }

    return agent_graph.invoke(
        initial_state,
        config={
            "recursion_limit": 15,
        },
    )
def get_agent_metrics():
    """Return performance metrics for all tracked agents."""
    return agent_metrics.get_metrics()