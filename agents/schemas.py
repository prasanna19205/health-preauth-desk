
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


# Types of hospital admission
class AdmissionType(str, Enum):
    PLANNED_SURGICAL = "planned_surgical"
    DAY_CARE = "day_care"
    EMERGENCY = "emergency"
    MATERNITY = "maternity"


# Status of a possible pre-existing condition
class PreExistingStatus(str, Enum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


# Hospital request structure
class PreAuthRequest(BaseModel):

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    patient_id: str = Field(min_length=1)
    policy_id: str = Field(min_length=1)

    policy_start_date: date
    admission_date: date

    procedure: str = Field(min_length=2)
    admission_type: AdmissionType

    room_category: str = Field(min_length=1)

    estimated_cost: Decimal = Field(gt=0)

    diagnosis: Optional[str] = None

    pre_existing_condition: PreExistingStatus = (
        PreExistingStatus.UNKNOWN
    )

    @field_validator("procedure", "room_category")
    @classmethod
    def validate_text(cls, value):
        if not value.strip():
            raise ValueError("Field cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.admission_date < self.policy_start_date:
            raise ValueError(
                "Admission date cannot be before policy start date"
            )
        return self


# Possible recommendation routes
class CoverageRecommendation(str, Enum):
    APPROVE_RECOMMENDED = "approve-recommended"
    QUERY_TO_HOSPITAL = "query-to-hospital"
    MEDICAL_REVIEW = "medical-review"


# Structured result returned by an agent
class AgentResult(BaseModel):

    recommendation: CoverageRecommendation
    reason: str
    supporting_clauses: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    requires_human_review: bool = False

class RequestAnalysis(BaseModel):
    """Structured findings produced by Agent 1."""

    admission_type: AdmissionType
    procedure: str
    policy_age_months: int

    investigation_checks: list[str] = Field(
        default_factory=list
    )

    missing_information: list[str] = Field(
        default_factory=list
    )

    escalation_flags: list[str] = Field(
        default_factory=list
    )

class CoverageInvestigation(BaseModel):
    """Evidence collected by Agent 2."""

    retrieved_clauses: list[dict] = Field(
        default_factory=list
    )

    checks_performed: list[str] = Field(
        default_factory=list
    )

    unresolved_checks: list[str] = Field(
        default_factory=list
    )

    investigation_notes: list[str] = Field(
        default_factory=list
    )
