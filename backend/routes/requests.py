
from typing import Optional, Literal

from fastapi import APIRouter, HTTPException, Query, status

from agents.schemas import PreAuthRequest
from backend.schemas import (
    JobSubmissionResponse,
    JobStatusResponse,
    JobResultResponse,
    JobHistoryResponse,
)
from backend.services.job_manager import job_manager

router = APIRouter(
    prefix="/requests",
    tags=["Pre-Authorisation Requests"],
)

@router.post(
    "",
    response_model=JobSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_request(request: PreAuthRequest):
    """Submit a pre-authorisation request for assessment."""

    job = job_manager.submit_job(request)

    return JobSubmissionResponse(
        job_id=job["job_id"],
        status=job["status"],
        message="Pre-authorisation request submitted successfully.",
    )

@router.get(
    "",
    response_model=JobHistoryResponse,
)
async def list_requests(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    request_status: Optional[
        Literal["queued", "running", "completed", "failed"]
    ] = Query(default=None, alias="status"),
):
    """Retrieve paginated request history with an optional status filter."""

    return job_manager.list_jobs(
        limit=limit,
        offset=offset,
        status=request_status,
    )

@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
)
async def get_request_status(job_id: str):
    """Retrieve the current status of a submitted request."""

    job = job_manager.get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    return job

@router.get(
    "/{job_id}/result",
    response_model=JobResultResponse,
)
async def get_request_result(job_id: str):
    """Retrieve the result or error of a submitted request."""

    result = job_manager.get_job_result(job_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    return result