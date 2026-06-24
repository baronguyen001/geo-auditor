"""Rule protocol and a small helper for building :class:`RuleResult`."""

from __future__ import annotations

from typing import Protocol

from geo_auditor.models import Category, Document, RuleResult, Severity


def result(
    rule: Rule,
    score: float,
    detail: str,
    fix: str,
) -> RuleResult:
    """Clamp *score* to [0, 1] and wrap it with the rule's metadata."""
    clamped = max(0.0, min(1.0, score))
    return RuleResult(
        rule_id=rule.id,
        title=rule.title,
        category=rule.category,
        weight=rule.weight,
        score=clamped,
        severity=Severity.from_score(clamped),
        detail=detail,
        fix=fix,
    )


class Rule(Protocol):
    """A single answer-engine heuristic."""

    id: str
    title: str
    category: Category
    weight: float

    def check(self, doc: Document) -> RuleResult: ...


class BaseRule:
    """Convenience base so concrete rules only implement :meth:`check`."""

    id: str = ""
    title: str = ""
    category: Category = Category.STRUCTURE
    weight: float = 1.0

    def check(self, doc: Document) -> RuleResult:  # pragma: no cover - overridden
        raise NotImplementedError
