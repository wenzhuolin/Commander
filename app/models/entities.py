import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    owner: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    subprojects: Mapped[list["SubProject"]] = relationship(back_populates="program")


class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    stages: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    subprojects: Mapped[list["SubProject"]] = relationship(back_populates="workflow_template")


class SubProject(Base):
    __tablename__ = "subprojects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    program_id: Mapped[str] = mapped_column(String(36), ForeignKey("programs.id"), nullable=False)
    workflow_template_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("workflow_templates.id"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    owner: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    program: Mapped["Program"] = relationship(back_populates="subprojects")
    workflow_template: Mapped["WorkflowTemplate"] = relationship(back_populates="subprojects")
    gate_rules: Mapped[list["GateRule"]] = relationship(back_populates="subproject")
    gate_checks: Mapped[list["GateCheck"]] = relationship(back_populates="subproject")
    review_records: Mapped[list["ReviewRecord"]] = relationship(back_populates="subproject")
    release_tickets: Mapped[list["ReleaseTicket"]] = relationship(back_populates="subproject")
    quality_snapshots: Mapped[list["QualityMetricSnapshot"]] = relationship(back_populates="subproject")


class GateRule(Base):
    __tablename__ = "gate_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subproject_id: Mapped[str] = mapped_column(String(36), ForeignKey("subprojects.id"), nullable=False)
    gate_name: Mapped[str] = mapped_column(String(60), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(100), nullable=False)
    operator: Mapped[str] = mapped_column(String(5), nullable=False)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_text: Mapped[str | None] = mapped_column(String(120), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="blocker", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    subproject: Mapped["SubProject"] = relationship(back_populates="gate_rules")


class GateCheck(Base):
    __tablename__ = "gate_checks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subproject_id: Mapped[str] = mapped_column(String(36), ForeignKey("subprojects.id"), nullable=False)
    gate_name: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    blocker_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warning_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    input_metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    failures: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    subproject: Mapped["SubProject"] = relationship(back_populates="gate_checks")


class ReviewRecord(Base):
    __tablename__ = "review_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subproject_id: Mapped[str] = mapped_column(String(36), ForeignKey("subprojects.id"), nullable=False)
    review_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    participants: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    action_items: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    subproject: Mapped["SubProject"] = relationship(back_populates="review_records")


class ReleaseTicket(Base):
    __tablename__ = "release_tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subproject_id: Mapped[str] = mapped_column(String(36), ForeignKey("subprojects.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    rollback_plan: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="approved", nullable=False)
    review_record_id: Mapped[str] = mapped_column(String(36), ForeignKey("review_records.id"), nullable=False)
    gate_check_id: Mapped[str] = mapped_column(String(36), ForeignKey("gate_checks.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    subproject: Mapped["SubProject"] = relationship(back_populates="release_tickets")


class QualityMetricSnapshot(Base):
    __tablename__ = "quality_metric_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subproject_id: Mapped[str] = mapped_column(String(36), ForeignKey("subprojects.id"), nullable=False)
    iteration_name: Mapped[str] = mapped_column(String(120), nullable=False)
    build_success_rate: Mapped[float] = mapped_column(Float, nullable=False)
    unit_test_pass_rate: Mapped[float] = mapped_column(Float, nullable=False)
    core_coverage: Mapped[float] = mapped_column(Float, nullable=False)
    blocker_defect_open: Mapped[int] = mapped_column(Integer, nullable=False)
    defect_escape_rate: Mapped[float] = mapped_column(Float, nullable=False)
    cfr: Mapped[float] = mapped_column(Float, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    subproject: Mapped["SubProject"] = relationship(back_populates="quality_snapshots")


class IntegrationEvent(Base):
    __tablename__ = "integration_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_system: Mapped[str] = mapped_column(String(60), nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    reference_id: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    subproject_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("subprojects.id"), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
