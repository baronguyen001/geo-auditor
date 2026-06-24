"""Aggregate rule results into a weighted 0-100 score with a letter grade."""

from __future__ import annotations

from collections.abc import Sequence

from geo_auditor.models import AuditReport, Category, Document, RuleResult
from geo_auditor.rules import ALL_RULES, audit
from geo_auditor.rules.base import Rule

_GRADE_BANDS = (
    (90, "A"),
    (80, "B"),
    (70, "C"),
    (60, "D"),
    (0, "F"),
)


def grade_for(score: int) -> str:
    """Map a 0-100 *score* to a letter grade."""
    for threshold, letter in _GRADE_BANDS:
        if score >= threshold:
            return letter
    return "F"  # pragma: no cover - unreachable, last band is 0


def _weighted_percent(results: Sequence[RuleResult]) -> int:
    total_weight = sum(r.weight for r in results)
    if total_weight == 0:
        return 0
    earned = sum(r.weight * r.score for r in results)
    return round(100 * earned / total_weight)


def build_report(
    doc: Document,
    rules: Sequence[Rule] = ALL_RULES,
) -> AuditReport:
    """Audit *doc* and assemble a full :class:`AuditReport`."""
    results = audit(doc, rules)
    overall = _weighted_percent(results)
    by_category: dict[Category, int] = {}
    for category in Category:
        bucket = [r for r in results if r.category is category]
        if bucket:
            by_category[category] = _weighted_percent(bucket)
    return AuditReport(
        score=overall,
        grade=grade_for(overall),
        results=results,
        by_category=by_category,
    )
