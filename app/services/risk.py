from app.models.entities import QualityMetricSnapshot


def calculate_risk_score(snapshot: QualityMetricSnapshot) -> tuple[int, str]:
    score = 0

    if snapshot.build_success_rate < 0.90:
        score += 2
    if snapshot.unit_test_pass_rate < 0.95:
        score += 2
    if snapshot.core_coverage < 0.80:
        score += 1
    if snapshot.blocker_defect_open > 0:
        score += 3
    if snapshot.defect_escape_rate > 0.05:
        score += 2
    if snapshot.cfr > 0.20:
        score += 2

    if score >= 6:
        level = "red"
    elif score >= 3:
        level = "yellow"
    else:
        level = "green"

    return score, level
