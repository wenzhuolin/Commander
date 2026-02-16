from typing import Any


VALID_OPERATORS = {"==", ">=", "<=", ">", "<"}


def _to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value.strip())
    raise ValueError(f"无法转换为数字: {value}")


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "==":
        return actual == expected

    actual_num = _to_float(actual)
    expected_num = _to_float(expected)

    if operator == ">=":
        return actual_num >= expected_num
    if operator == "<=":
        return actual_num <= expected_num
    if operator == ">":
        return actual_num > expected_num
    if operator == "<":
        return actual_num < expected_num
    raise ValueError(f"不支持的操作符: {operator}")


def evaluate_gate_rules(rules: list[Any], metrics: dict[str, Any]) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    blocker_failures = 0
    warning_failures = 0

    for rule in rules:
        if not rule.enabled:
            continue
        if rule.operator not in VALID_OPERATORS:
            raise ValueError(f"规则操作符非法: {rule.operator}")

        expected = rule.target_value if rule.target_value is not None else rule.target_text
        actual = metrics.get(rule.metric_key)

        if expected is None:
            failures.append(
                {
                    "metric_key": rule.metric_key,
                    "expected": "未配置目标值",
                    "actual": str(actual),
                    "severity": rule.severity,
                    "message": "规则缺少 target_value 或 target_text",
                }
            )
        elif actual is None:
            failures.append(
                {
                    "metric_key": rule.metric_key,
                    "expected": str(expected),
                    "actual": "None",
                    "severity": rule.severity,
                    "message": "输入指标缺失",
                }
            )
        else:
            passed = _compare(actual=actual, operator=rule.operator, expected=expected)
            if not passed:
                failures.append(
                    {
                        "metric_key": rule.metric_key,
                        "expected": f"{rule.operator} {expected}",
                        "actual": str(actual),
                        "severity": rule.severity,
                        "message": "未达到卡点要求",
                    }
                )

    for failure in failures:
        if failure["severity"].lower() == "blocker":
            blocker_failures += 1
        else:
            warning_failures += 1

    if blocker_failures > 0:
        status = "failed"
    elif warning_failures > 0:
        status = "passed_with_warnings"
    else:
        status = "passed"

    return {
        "status": status,
        "blocker_failures": blocker_failures,
        "warning_failures": warning_failures,
        "failures": failures,
    }
