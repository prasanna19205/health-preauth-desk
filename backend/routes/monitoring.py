
from fastapi import APIRouter

from agents.graph import get_agent_metrics

router = APIRouter(
    prefix="/monitoring",
    tags=["Monitoring"],
)


@router.get("/agent-metrics")
async def get_metrics():
    """Retrieve execution metrics for the AI agents."""
    return get_agent_metrics()
