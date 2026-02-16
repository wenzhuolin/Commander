import os

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from app.core.database import Base, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


def _create_program_template_subproject(client: TestClient) -> tuple[str, str, str]:
    program = client.post(
        "/api/v1/programs",
        json={"name": "项目群A", "description": "测试用项目群", "owner": "PM"},
    )
    assert program.status_code == 201
    program_id = program.json()["id"]

    template = client.post(
        "/api/v1/workflow-templates",
        json={
            "name": "默认模板",
            "version": "1.0.0",
            "description": "标准流程",
            "stages": ["需求", "设计", "开发", "联调", "转测", "发布"],
            "is_active": True,
        },
    )
    assert template.status_code == 201
    template_id = template.json()["id"]

    subproject = client.post(
        "/api/v1/subprojects",
        json={
            "program_id": program_id,
            "workflow_template_id": template_id,
            "name": "子项目A",
            "owner": "技术负责人",
            "status": "active",
        },
    )
    assert subproject.status_code == 201
    subproject_id = subproject.json()["id"]
    return program_id, template_id, subproject_id


def test_end_to_end_flow() -> None:
    client = TestClient(app)
    program_id, _, subproject_id = _create_program_template_subproject(client)

    for rule in [
        {"metric_key": "build_status", "operator": "==", "target_text": "SUCCESS", "severity": "blocker"},
        {"metric_key": "unit_test_pass_rate", "operator": ">=", "target_value": 0.95, "severity": "blocker"},
        {"metric_key": "blocker_defect_open", "operator": "==", "target_value": 0, "severity": "blocker"},
    ]:
        response = client.post(f"/api/v1/subprojects/{subproject_id}/gate-rules", json=rule)
        assert response.status_code == 201

    gate_check = client.post(
        f"/api/v1/subprojects/{subproject_id}/gate-checks",
        json={
            "gate_name": "dev_to_test",
            "metrics": {"build_status": "SUCCESS", "unit_test_pass_rate": 0.97, "blocker_defect_open": 0},
        },
    )
    assert gate_check.status_code == 201
    assert gate_check.json()["status"] == "passed"
    gate_check_id = gate_check.json()["id"]

    review = client.post(
        f"/api/v1/subprojects/{subproject_id}/reviews",
        json={
            "review_type": "release_review",
            "title": "发布评审",
            "decision": "approved",
            "participants": ["PM", "QA", "TechLead"],
            "action_items": [],
        },
    )
    assert review.status_code == 201
    review_id = review.json()["id"]

    release = client.post(
        f"/api/v1/subprojects/{subproject_id}/release-tickets",
        json={
            "version": "v1.0.0",
            "scope": "支付域需求与缺陷修复",
            "rollback_plan": "回滚到前一稳定版本",
            "risk_level": "medium",
            "review_record_id": review_id,
            "gate_check_id": gate_check_id,
        },
    )
    assert release.status_code == 201
    assert release.json()["status"] == "approved"

    snapshot = client.post(
        f"/api/v1/subprojects/{subproject_id}/quality-snapshots",
        json={
            "iteration_name": "2026-W07",
            "build_success_rate": 0.96,
            "unit_test_pass_rate": 0.97,
            "core_coverage": 0.82,
            "blocker_defect_open": 0,
            "defect_escape_rate": 0.01,
            "cfr": 0.10,
        },
    )
    assert snapshot.status_code == 201

    dashboard = client.get(f"/api/v1/dashboard/programs/{program_id}")
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["total_subprojects"] == 1
    assert body["risk_distribution"]["green"] == 1


def test_gate_fail_prevents_release() -> None:
    client = TestClient(app)
    _, _, subproject_id = _create_program_template_subproject(client)

    response = client.post(
        f"/api/v1/subprojects/{subproject_id}/gate-rules",
        json={"metric_key": "blocker_defect_open", "operator": "==", "target_value": 0, "severity": "blocker"},
    )
    assert response.status_code == 201

    gate_check = client.post(
        f"/api/v1/subprojects/{subproject_id}/gate-checks",
        json={"gate_name": "dev_to_test", "metrics": {"blocker_defect_open": 3}},
    )
    assert gate_check.status_code == 201
    assert gate_check.json()["status"] == "failed"
    gate_check_id = gate_check.json()["id"]

    review = client.post(
        f"/api/v1/subprojects/{subproject_id}/reviews",
        json={
            "review_type": "release_review",
            "title": "发布评审",
            "decision": "approved",
            "participants": ["PM", "QA"],
            "action_items": [],
        },
    )
    assert review.status_code == 201
    review_id = review.json()["id"]

    release = client.post(
        f"/api/v1/subprojects/{subproject_id}/release-tickets",
        json={
            "version": "v1.0.1",
            "scope": "发布失败场景",
            "rollback_plan": "回滚",
            "risk_level": "high",
            "review_record_id": review_id,
            "gate_check_id": gate_check_id,
        },
    )
    assert release.status_code == 400
    assert "卡点未通过" in release.json()["detail"]
