"""Rule registry and the :func:`audit` entry point.

``ALL_RULES`` is the canonical, ordered list of every heuristic geo-auditor
applies. ``audit`` simply runs each rule against a document.
"""

from __future__ import annotations

from collections.abc import Sequence

from geo_auditor.models import Document, RuleResult
from geo_auditor.rules.authority import AuthorRule, CitationsRule, StatisticsRule
from geo_auditor.rules.base import Rule
from geo_auditor.rules.freshness import FreshnessRule
from geo_auditor.rules.machine import (
    EntityClarityRule,
    FaqRule,
    JsonLdRule,
    MetaTagsRule,
)
from geo_auditor.rules.multimedia import (
    AltTextRule,
    CanonicalRule,
    SocialCardRule,
    TableDataRule,
)
from geo_auditor.rules.readability import (
    DescriptiveAnchorRule,
    ParagraphLengthRule,
    SentenceLengthRule,
)
from geo_auditor.rules.structure import (
    AnswerFirstRule,
    ContentDepthRule,
    HeadingHierarchyRule,
    QuestionHeadingsRule,
    ScannableRule,
    TldrSummaryRule,
)

ALL_RULES: tuple[Rule, ...] = (
    AnswerFirstRule(),
    QuestionHeadingsRule(),
    ScannableRule(),
    HeadingHierarchyRule(),
    ContentDepthRule(),
    TldrSummaryRule(),
    JsonLdRule(),
    FaqRule(),
    MetaTagsRule(),
    EntityClarityRule(),
    StatisticsRule(),
    CitationsRule(),
    AuthorRule(),
    FreshnessRule(),
    AltTextRule(),
    TableDataRule(),
    CanonicalRule(),
    SocialCardRule(),
    SentenceLengthRule(),
    ParagraphLengthRule(),
    DescriptiveAnchorRule(),
)


def audit(doc: Document, rules: Sequence[Rule] = ALL_RULES) -> list[RuleResult]:
    """Run every rule in *rules* against *doc* and return the results."""
    return [rule.check(doc) for rule in rules]


__all__ = [
    "ALL_RULES",
    "AltTextRule",
    "CanonicalRule",
    "DescriptiveAnchorRule",
    "ParagraphLengthRule",
    "Rule",
    "SentenceLengthRule",
    "SocialCardRule",
    "TableDataRule",
    "audit",
]
