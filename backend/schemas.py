
from typing import Any, Optional

from pydantic import BaseModel

class JobSubmissionResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    created_at: str
    updated_at: str

class JobResultResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None

class JobHistoryItem(BaseModel):
    job_id: str
    status: str
    patient_id: Optional[str] = None
    policy_id: Optional[str] = None
    procedure: Optional[str] = None
    admission_date: Optional[str] = None
    recommendation: Optional[str] = None
    created_at: str
    updated_at: str
    error: Optional[str] = None

class JobHistoryResponse(BaseModel):
    items: list[JobHistoryItem]
    total: int
    limit: int
    offset: int