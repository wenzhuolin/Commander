from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProgramCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = ""
    owner: str = Field(min_length=2, max_length=100)


class ProgramRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    owner: str
    created_at: datetime


class WorkflowTemplateCreate(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str = ""
    stages: list[str] = Field(min_length=1)
    is_active: bool = True


class WorkflowTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    version: str
    description: str
    stages: list[str]
    is_active: bool
    created_at: datetime


class SubProjectCreate(BaseModel):
    program_id: str
    workflow_template_id: str | None = None
    name: str
    owner: str
    status: str = "active"


class SubProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    program_id: str
    workflow_template_id: str | None
    name: str
    owner: str
    status: str
    created_at: datetime


class GateRuleCreate(BaseModel):
    gate_name: str = "dev_to_test"
    metric_key: str
    operator: str
    target_value: float | None = None
    target_text: str | None = None
    severity: str = "blocker"
    enabled: bool = True
    version: str = "1.0.0"


class GateRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subproject_id: str
    gate_name: str
    metric_key: str
    operator: str
    target_value: float | None
    target_text: str | None
    severity: str
    enabled: bool
    version: str
    created_at: datetime


class GateCheckRequest(BaseModel):
    gate_name: str = "dev_to_test"
    metrics: dict[str, Any]


class GateFailure(BaseModel):
    metric_key: str
    expected: str
    actual: str
    severity: str
    message: str


class GateCheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subproject_id: str
    gate_name: str
    status: str
    blocker_failures: int
    warning_failures: int
    input_metrics: dict[str, Any]
    failures: list[dict[str, Any]]
    checked_at: datetime


class ReviewCreate(BaseModel):
    review_type: str
    title: str
    decision: str
    participants: list[str] = Field(default_factory=list)
    action_items: list[dict[str, Any]] = Field(default_factory=list)


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subproject_id: str
    review_type: str
    title: str
    decision: str
    participants: list[str]
    action_items: list[dict[str, Any]]
    created_at: datetime


class ReleaseTicketCreate(BaseModel):
    version: str
    scope: str
    rollback_plan: str
    risk_level: str = "medium"
    review_record_id: str
    gate_check_id: str


class ReleaseTicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subproject_id: str
    version: str
    scope: str
    rollback_plan: str
    risk_level: str
    status: str
    review_record_id: str
    gate_check_id: str
    created_at: datetime


class QualitySnapshotCreate(BaseModel):
    iteration_name: str
    build_success_rate: float
    unit_test_pass_rate: float
    core_coverage: float
    blocker_defect_open: int
    defect_escape_rate: float
    cfr: float


class QualitySnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subproject_id: str
    iteration_name: str
    build_success_rate: float
    unit_test_pass_rate: float
    core_coverage: float
    blocker_defect_open: int
    defect_escape_rate: float
    cfr: float
    captured_at: datetime


class IntegrationEventCreate(BaseModel):
    source_system: str
    event_type: str
    reference_id: str
    payload: dict[str, Any]
    subproject_id: str | None = None


class IntegrationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_system: str
    event_type: str
    reference_id: str
    payload: dict[str, Any]
    subproject_id: str | None
    received_at: datetime


class SubProjectRiskSummary(BaseModel):
    subproject_id: str
    subproject_name: str
    risk_level: str
    score: int


class ProgramDashboardRead(BaseModel):
    program_id: str
    program_name: str
    total_subprojects: int
    gate_pass_rate: float
    risk_distribution: dict[str, int]
    subproject_risks: list[SubProjectRiskSummary]
