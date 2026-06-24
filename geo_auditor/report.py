"""Render an :class:`AuditReport` as text, JSON, or Markdown.

All output is ASCII-only on purpose: decorative Unicode (arrows, em dashes)
crashes on Windows cp1252 consoles, which would turn the CI matrix red.
"""

from __future__ import annotations

import json

from geo_auditor.models import AuditReport, RuleResult, Severity

_SEVERITY_TAG = {
    Severity.PASS: "PASS",
    Severity.WARN: "WARN",
    Severity.FAIL: "FAIL",
}


def _sorted_results(report: AuditReport) -> list[RuleResult]:
    # Worst first so the most impactful fixes are read first; stable within a
    # severity by descending weight then rule id.
    order = {Severity.FAIL: 0, Severity.WARN: 1, Severity.PASS: 2}
    return sorted(
        report.results,
        key=lambda r: (order[r.severity], -r.weight, r.rule_id),
    )


def render_text(report: AuditReport) -> str:
    lines = [
        "GEO/AEO readiness report",
        "========================",
        f"Score: {report.score}/100  (grade {report.grade})",
        "",
        "By category:",
    ]
    for category, value in report.by_category.items():
        lines.append(f"  {category.value:<16} {value:>3}/100")
    lines.append("")
    lines.append("Checks (worst first):")
    for r in _sorted_results(report):
        tag = _SEVERITY_TAG[r.severity]
        lines.append(f"  [{tag}] {r.title} ({r.rule_id}) - {int(r.score * 100)}%")
        lines.append(f"        {r.detail}")
        if r.fix:
            lines.append(f"        fix: {r.fix}")
    return "\n".join(lines)


def render_json(report: AuditReport) -> str:
    payload = {
        "score": report.score,
        "grade": report.grade,
        "by_category": {c.value: v for c, v in report.by_category.items()},
        "results": [
            {
                "rule_id": r.rule_id,
                "title": r.title,
                "category": r.category.value,
                "weight": r.weight,
                "score": round(r.score, 4),
                "severity": r.severity.value,
                "detail": r.detail,
                "fix": r.fix,
            }
            for r in report.results
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=True)


def render_markdown(report: AuditReport) -> str:
    lines = [
        "# GEO/AEO readiness report",
        "",
        f"**Score: {report.score}/100** (grade {report.grade})",
        "",
        "| Category | Score |",
        "| --- | --- |",
    ]
    for category, value in report.by_category.items():
        lines.append(f"| {category.value} | {value}/100 |")
    lines.append("")
    lines.append("| Result | Check | Score | Detail | Fix |")
    lines.append("| --- | --- | --- | --- | --- |")
    for r in _sorted_results(report):
        tag = _SEVERITY_TAG[r.severity]
        fix = r.fix or "-"
        lines.append(f"| {tag} | {r.title} | {int(r.score * 100)}% | {r.detail} | {fix} |")
    return "\n".join(lines)
