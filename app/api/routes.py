from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import (
    GateCheck,
    GateRule,
    IntegrationEvent,
    Program,
    QualityMetricSnapshot,
    ReleaseTicket,
    ReviewRecord,
    SubProject,
    WorkflowTemplate,
)
from app.schemas.api import (
    GateCheckRead,
    GateCheckRequest,
    GateRuleCreate,
    GateRuleRead,
    IntegrationEventCreate,
    IntegrationEventRead,
    ProgramCreate,
    ProgramDashboardRead,
    ProgramRead,
    QualitySnapshotCreate,
    QualitySnapshotRead,
    ReleaseTicketCreate,
    ReleaseTicketRead,
    ReviewCreate,
    ReviewRead,
    SubProjectCreate,
    SubProjectRead,
    SubProjectRiskSummary,
    WorkflowTemplateCreate,
    WorkflowTemplateRead,
)
from app.services.gate_evaluator import evaluate_gate_rules
from app.services.risk import calculate_risk_score

router = APIRouter()


def _get_subproject_or_404(db: Session, subproject_id: str) -> SubProject:
    subproject = db.get(SubProject, subproject_id)
    if not subproject:
        raise HTTPException(status_code=404, detail="子项目不存在")
    return subproject


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/programs", response_model=ProgramRead, status_code=status.HTTP_201_CREATED)
def create_program(payload: ProgramCreate, db: Session = Depends(get_db)) -> Program:
    existing = db.scalar(select(Program).where(Program.name == payload.name))
    if existing:
        raise HTTPException(status_code=400, detail="项目群名称已存在")

    program = Program(name=payload.name, description=payload.description, owner=payload.owner)
    db.add(program)
    db.commit()
    db.refresh(program)
    return program


@router.get("/programs", response_model=list[ProgramRead])
def list_programs(db: Session = Depends(get_db)) -> list[Program]:
    return list(db.scalars(select(Program).order_by(desc(Program.created_at))).all())


@router.post("/workflow-templates", response_model=WorkflowTemplateRead, status_code=status.HTTP_201_CREATED)
def create_workflow_template(payload: WorkflowTemplateCreate, db: Session = Depends(get_db)) -> WorkflowTemplate:
    template = WorkflowTemplate(
        name=payload.name,
        version=payload.version,
        description=payload.description,
        stages=payload.stages,
        is_active=payload.is_active,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/workflow-templates", response_model=list[WorkflowTemplateRead])
def list_workflow_templates(db: Session = Depends(get_db)) -> list[WorkflowTemplate]:
    return list(db.scalars(select(WorkflowTemplate).order_by(desc(WorkflowTemplate.created_at))).all())


@router.post("/subprojects", response_model=SubProjectRead, status_code=status.HTTP_201_CREATED)
def create_subproject(payload: SubProjectCreate, db: Session = Depends(get_db)) -> SubProject:
    program = db.get(Program, payload.program_id)
    if not program:
        raise HTTPException(status_code=404, detail="所属项目群不存在")

    if payload.workflow_template_id:
        template = db.get(WorkflowTemplate, payload.workflow_template_id)
        if not template:
            raise HTTPException(status_code=404, detail="流程模板不存在")

    subproject = SubProject(
        program_id=payload.program_id,
        workflow_template_id=payload.workflow_template_id,
        name=payload.name,
        owner=payload.owner,
        status=payload.status,
    )
    db.add(subproject)
    db.commit()
    db.refresh(subproject)
    return subproject


@router.get("/subprojects/{subproject_id}", response_model=SubProjectRead)
def get_subproject(subproject_id: str, db: Session = Depends(get_db)) -> SubProject:
    return _get_subproject_or_404(db, subproject_id)


@router.post("/subprojects/{subproject_id}/gate-rules", response_model=GateRuleRead, status_code=status.HTTP_201_CREATED)
def create_gate_rule(subproject_id: str, payload: GateRuleCreate, db: Session = Depends(get_db)) -> GateRule:
    _get_subproject_or_404(db, subproject_id)
    if payload.operator not in {"==", ">=", "<=", ">", "<"}:
        raise HTTPException(status_code=400, detail="operator 只支持 ==, >=, <=, >, <")
    if payload.target_value is None and payload.target_text is None:
        raise HTTPException(status_code=400, detail="target_value 和 target_text 不能同时为空")

    rule = GateRule(
        subproject_id=subproject_id,
        gate_name=payload.gate_name,
        metric_key=payload.metric_key,
        operator=payload.operator,
        target_value=payload.target_value,
        target_text=payload.target_text,
        severity=payload.severity.lower(),
        enabled=payload.enabled,
        version=payload.version,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/subprojects/{subproject_id}/gate-rules", response_model=list[GateRuleRead])
def list_gate_rules(
    subproject_id: str,
    gate_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[GateRule]:
    _get_subproject_or_404(db, subproject_id)
    query = select(GateRule).where(GateRule.subproject_id == subproject_id).order_by(desc(GateRule.created_at))
    if gate_name:
        query = query.where(GateRule.gate_name == gate_name)
    return list(db.scalars(query).all())


@router.post("/subprojects/{subproject_id}/gate-checks", response_model=GateCheckRead, status_code=status.HTTP_201_CREATED)
def check_gate(subproject_id: str, payload: GateCheckRequest, db: Session = Depends(get_db)) -> GateCheck:
    _get_subproject_or_404(db, subproject_id)
    rules = list(
        db.scalars(
            select(GateRule).where(
                GateRule.subproject_id == subproject_id,
                GateRule.gate_name == payload.gate_name,
                GateRule.enabled.is_(True),
            )
        ).all()
    )
    if not rules:
        raise HTTPException(status_code=400, detail="该子项目下没有可用的卡点规则")

    result = evaluate_gate_rules(rules=rules, metrics=payload.metrics)
    gate_check = GateCheck(
        subproject_id=subproject_id,
        gate_name=payload.gate_name,
        status=result["status"],
        blocker_failures=result["blocker_failures"],
        warning_failures=result["warning_failures"],
        input_metrics=payload.metrics,
        failures=result["failures"],
    )
    db.add(gate_check)
    db.commit()
    db.refresh(gate_check)
    return gate_check


@router.post("/subprojects/{subproject_id}/reviews", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
def create_review(subproject_id: str, payload: ReviewCreate, db: Session = Depends(get_db)) -> ReviewRecord:
    _get_subproject_or_404(db, subproject_id)
    review = ReviewRecord(
        subproject_id=subproject_id,
        review_type=payload.review_type,
        title=payload.title,
        decision=payload.decision.lower(),
        participants=payload.participants,
        action_items=payload.action_items,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@router.post("/subprojects/{subproject_id}/release-tickets", response_model=ReleaseTicketRead, status_code=status.HTTP_201_CREATED)
def create_release_ticket(subproject_id: str, payload: ReleaseTicketCreate, db: Session = Depends(get_db)) -> ReleaseTicket:
    _get_subproject_or_404(db, subproject_id)

    review = db.get(ReviewRecord, payload.review_record_id)
    if not review or review.subproject_id != subproject_id:
        raise HTTPException(status_code=400, detail="评审记录不存在或不属于当前子项目")
    if review.decision not in {"approved", "pass", "passed"}:
        raise HTTPException(status_code=400, detail="评审未通过，不允许创建发布单")

    gate_check = db.get(GateCheck, payload.gate_check_id)
    if not gate_check or gate_check.subproject_id != subproject_id:
        raise HTTPException(status_code=400, detail="卡点检查记录不存在或不属于当前子项目")
    if gate_check.status == "failed":
        raise HTTPException(status_code=400, detail="卡点未通过，不允许创建发布单")

    release = ReleaseTicket(
        subproject_id=subproject_id,
        version=payload.version,
        scope=payload.scope,
        rollback_plan=payload.rollback_plan,
        risk_level=payload.risk_level,
        status="approved",
        review_record_id=payload.review_record_id,
        gate_check_id=payload.gate_check_id,
    )
    db.add(release)
    db.commit()
    db.refresh(release)
    return release


@router.post(
    "/subprojects/{subproject_id}/quality-snapshots",
    response_model=QualitySnapshotRead,
    status_code=status.HTTP_201_CREATED,
)
def create_quality_snapshot(subproject_id: str, payload: QualitySnapshotCreate, db: Session = Depends(get_db)) -> QualityMetricSnapshot:
    _get_subproject_or_404(db, subproject_id)
    snapshot = QualityMetricSnapshot(
        subproject_id=subproject_id,
        iteration_name=payload.iteration_name,
        build_success_rate=payload.build_success_rate,
        unit_test_pass_rate=payload.unit_test_pass_rate,
        core_coverage=payload.core_coverage,
        blocker_defect_open=payload.blocker_defect_open,
        defect_escape_rate=payload.defect_escape_rate,
        cfr=payload.cfr,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.get("/dashboard/programs/{program_id}", response_model=ProgramDashboardRead)
def get_program_dashboard(program_id: str, db: Session = Depends(get_db)) -> ProgramDashboardRead:
    program = db.get(Program, program_id)
    if not program:
        raise HTTPException(status_code=404, detail="项目群不存在")

    subprojects = list(db.scalars(select(SubProject).where(SubProject.program_id == program_id)).all())
    subproject_ids = [item.id for item in subprojects]

    gate_pass_rate = 1.0
    if subproject_ids:
        checks = list(db.scalars(select(GateCheck).where(GateCheck.subproject_id.in_(subproject_ids))).all())
        if checks:
            passed_count = sum(1 for item in checks if item.status != "failed")
            gate_pass_rate = passed_count / len(checks)

    risk_distribution: dict[str, int] = {"green": 0, "yellow": 0, "red": 0}
    subproject_risks: list[SubProjectRiskSummary] = []
    for subproject in subprojects:
        latest_snapshot = db.scalar(
            select(QualityMetricSnapshot)
            .where(QualityMetricSnapshot.subproject_id == subproject.id)
            .order_by(desc(QualityMetricSnapshot.captured_at))
        )

        if latest_snapshot:
            score, level = calculate_risk_score(latest_snapshot)
        else:
            score, level = 0, "green"

        risk_distribution[level] = risk_distribution.get(level, 0) + 1
        subproject_risks.append(
            SubProjectRiskSummary(
                subproject_id=subproject.id,
                subproject_name=subproject.name,
                risk_level=level,
                score=score,
            )
        )

    return ProgramDashboardRead(
        program_id=program.id,
        program_name=program.name,
        total_subprojects=len(subprojects),
        gate_pass_rate=round(gate_pass_rate, 4),
        risk_distribution=risk_distribution,
        subproject_risks=subproject_risks,
    )


@router.post("/integrations/events", response_model=IntegrationEventRead, status_code=status.HTTP_201_CREATED)
def ingest_integration_event(payload: IntegrationEventCreate, db: Session = Depends(get_db)) -> IntegrationEvent:
    if payload.subproject_id:
        _get_subproject_or_404(db, payload.subproject_id)
    event = IntegrationEvent(
        source_system=payload.source_system,
        event_type=payload.event_type,
        reference_id=payload.reference_id,
        payload=payload.payload,
        subproject_id=payload.subproject_id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/integrations/events", response_model=list[IntegrationEventRead])
def list_integration_events(limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)) -> list[IntegrationEvent]:
    query = select(IntegrationEvent).order_by(desc(IntegrationEvent.received_at)).limit(limit)
    return list(db.scalars(query).all())


@router.get("/subprojects/{subproject_id}/overview")
def get_subproject_overview(subproject_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    subproject = _get_subproject_or_404(db, subproject_id)
    latest_gate = db.scalar(
        select(GateCheck).where(GateCheck.subproject_id == subproject_id).order_by(desc(GateCheck.checked_at))
    )
    latest_snapshot = db.scalar(
        select(QualityMetricSnapshot)
        .where(QualityMetricSnapshot.subproject_id == subproject_id)
        .order_by(desc(QualityMetricSnapshot.captured_at))
    )
    latest_release = db.scalar(
        select(ReleaseTicket).where(ReleaseTicket.subproject_id == subproject_id).order_by(desc(ReleaseTicket.created_at))
    )

    risk_level = "green"
    risk_score = 0
    if latest_snapshot:
        risk_score, risk_level = calculate_risk_score(latest_snapshot)

    return {
        "subproject_id": subproject.id,
        "subproject_name": subproject.name,
        "owner": subproject.owner,
        "status": subproject.status,
        "latest_gate_status": latest_gate.status if latest_gate else "unknown",
        "latest_release_status": latest_release.status if latest_release else "none",
        "risk_level": risk_level,
        "risk_score": risk_score,
    }
