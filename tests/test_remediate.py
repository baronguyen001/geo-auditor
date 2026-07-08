"""Tests for remediation plan rendering."""

from __future__ import annotations

import json

from geo_auditor.models import AuditReport, Category, RuleResult, Severity
from geo_auditor.remediate import (
    build_remediation,
    render_remediation_json,
    render_remediation_markdown,
    render_remediation_text,
)


def _result(
    rule_id: str,
    category: Category,
    weight: float,
    score: float,
    severity: Severity,
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        title=rule_id.title(),
        category=category,
        weight=weight,
        score=score,
        severity=severity,
        detail="detail",
        fix=f"Fix {rule_id}.",
    )


def _report() -> AuditReport:
    return AuditReport(
        score=50,
        grade="F",
        by_category={Category.STRUCTURE: 50},
        results=[
            _result("b-rule", Category.STRUCTURE, 2.0, 0.5, Severity.WARN),
            _result("a-rule", Category.AUTHORITY, 1.0, 0.0, Severity.FAIL),
            _result("c-rule", Category.FRESHNESS, 1.0, 1.0, Severity.PASS),
        ],
    )


def test_build_remediation_orders_by_projected_points_then_rule_id() -> None:
    plan = build_remediation(_report())
    assert [item.rule_id for item in plan.items] == ["a-rule", "b-rule"]
    assert plan.items[0].projected_points == 25.0
    assert plan.items[1].projected_points == 25.0
    assert plan.total_recoverable_points == 50.0


def test_build_remediation_top_limit() -> None:
    plan = build_remediation(_report(), top=1)
    assert [item.rule_id for item in plan.items] == ["a-rule"]
    assert plan.total_recoverable_points == 25.0


def test_render_remediation_formats_are_ascii() -> None:
    plan = build_remediation(_report())
    text = render_remediation_text(plan)
    markdown = render_remediation_markdown(plan)
    json_text = render_remediation_json(plan)
    assert all(ord(ch) < 128 for ch in text + markdown + json_text)
    assert "Total recoverable points: 50.00" in text
    assert markdown.startswith("# GEO/AEO remediation plan")
    data = json.loads(json_text)
    assert data["total_recoverable_points"] == 50.0
    assert data["items"][0]["rule_id"] == "a-rule"
