"""Build and render prioritized remediation plans."""

from __future__ import annotations

import json
from dataclasses import dataclass

from geo_auditor.models import AuditReport, Category, RuleResult, Severity

_SEVERITY_TAG = {
    Severity.WARN: "WARN",
    Severity.FAIL: "FAIL",
}


@dataclass(frozen=True)
class RemediationItem:
    """One actionable rule fix with its projected score impact."""

    rule_id: str
    title: str
    category: Category
    severity: Severity
    score: float
    fix: str
    projected_points: float


@dataclass(frozen=True)
class RemediationPlan:
    """Prioritized fixes for an audit report."""

    items: list[RemediationItem]
    total_recoverable_points: float


def build_remediation(report: AuditReport, *, top: int | None = None) -> RemediationPlan:
    """Build a worst-first remediation plan from an :class:`AuditReport`."""

    total_weight = sum(result.weight for result in report.results)
    actionable = [
        result for result in report.results if result.severity in {Severity.FAIL, Severity.WARN}
    ]
    ordered = sorted(actionable, key=lambda result: (-_weighted_loss(result), result.rule_id))
    if top is not None:
        ordered = ordered[: max(0, top)]
    items = [_item_from_result(result, total_weight) for result in ordered]
    return RemediationPlan(
        items=items,
        total_recoverable_points=sum(item.projected_points for item in items),
    )


def render_remediation_text(plan: RemediationPlan) -> str:
    """Render a remediation plan as plain text."""

    lines = [
        "GEO/AEO remediation plan",
        "========================",
        "",
        "Fixes (highest impact first):",
    ]
    if not plan.items:
        lines.append("  No failing or warning rules.")
    for index, item in enumerate(plan.items, start=1):
        tag = _SEVERITY_TAG[item.severity]
        lines.append(
            f"  {index}. [{tag}] {item.title} ({item.rule_id}) - "
            f"{int(item.score * 100)}%, +{item.projected_points:.2f} pts"
        )
        lines.append(f"     category: {item.category.value}")
        lines.append(f"     fix: {item.fix or 'No fix needed.'}")
    lines.append("")
    lines.append(f"Total recoverable points: {plan.total_recoverable_points:.2f}")
    return "\n".join(lines)


def render_remediation_markdown(plan: RemediationPlan) -> str:
    """Render a remediation plan as Markdown."""

    lines = [
        "# GEO/AEO remediation plan",
        "",
        "| Rank | Rule | Category | Severity | Score | Projected gain | Fix |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    if not plan.items:
        lines.append("| - | - | - | - | - | - | No failing or warning rules. |")
    for index, item in enumerate(plan.items, start=1):
        lines.append(
            f"| {index} | {item.title} (`{item.rule_id}`) | {item.category.value} | "
            f"{item.severity.value} | {int(item.score * 100)}% | "
            f"{item.projected_points:.2f} | {item.fix or '-'} |"
        )
    lines.append("")
    lines.append(f"**Total recoverable points:** {plan.total_recoverable_points:.2f}")
    return "\n".join(lines)


def render_remediation_json(plan: RemediationPlan) -> str:
    """Render a remediation plan as deterministic JSON."""

    payload = {
        "total_recoverable_points": round(plan.total_recoverable_points, 4),
        "items": [
            {
                "rule_id": item.rule_id,
                "title": item.title,
                "category": item.category.value,
                "severity": item.severity.value,
                "score": round(item.score, 4),
                "fix": item.fix,
                "projected_points": round(item.projected_points, 4),
            }
            for item in plan.items
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=True)


def _weighted_loss(result: RuleResult) -> float:
    return result.weight * (1.0 - result.score)


def _item_from_result(result: RuleResult, total_weight: float) -> RemediationItem:
    projected_points = 0.0
    if total_weight > 0:
        projected_points = 100 * _weighted_loss(result) / total_weight
    return RemediationItem(
        rule_id=result.rule_id,
        title=result.title,
        category=result.category,
        severity=result.severity,
        score=result.score,
        fix=result.fix,
        projected_points=projected_points,
    )
