from sqlalchemy import select

from app.core.database import SessionLocal, init_db
from app.models.entities import GateRule, Program, QualityMetricSnapshot, SubProject, WorkflowTemplate


def seed_demo_data() -> None:
    init_db()
    session = SessionLocal()
    try:
        existing = session.scalar(select(Program).where(Program.name == "集成平台项目群"))
        if existing:
            return

        program = Program(name="集成平台项目群", description="用于演示的项目群", owner="PMO")
        session.add(program)
        session.flush()

        template = WorkflowTemplate(
            name="标准研发流程",
            version="1.0.0",
            description="需求-设计-开发-联调-转测-发布",
            stages=["需求", "设计", "开发", "联调", "转测", "发布"],
        )
        session.add(template)
        session.flush()

        subproject = SubProject(
            program_id=program.id,
            workflow_template_id=template.id,
            name="支付域子项目",
            owner="张三",
            status="active",
        )
        session.add(subproject)
        session.flush()

        rules = [
            GateRule(
                subproject_id=subproject.id,
                gate_name="dev_to_test",
                metric_key="build_status",
                operator="==",
                target_text="SUCCESS",
                severity="blocker",
            ),
            GateRule(
                subproject_id=subproject.id,
                gate_name="dev_to_test",
                metric_key="unit_test_pass_rate",
                operator=">=",
                target_value=0.95,
                severity="blocker",
            ),
            GateRule(
                subproject_id=subproject.id,
                gate_name="dev_to_test",
                metric_key="blocker_defect_open",
                operator="==",
                target_value=0,
                severity="blocker",
            ),
        ]
        session.add_all(rules)

        snapshot = QualityMetricSnapshot(
            subproject_id=subproject.id,
            iteration_name="2026-W07",
            build_success_rate=0.96,
            unit_test_pass_rate=0.97,
            core_coverage=0.82,
            blocker_defect_open=0,
            defect_escape_rate=0.01,
            cfr=0.08,
        )
        session.add(snapshot)

        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    seed_demo_data()
    print("Demo data seeded.")
