"""Core data models for geo-auditor.

Everything here is a plain dataclass so reports serialize cleanly to JSON and
stay deterministic across runs (no timestamps, no ordering surprises).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Category(StrEnum):
    """The four pillars an answer engine cares about."""

    STRUCTURE = "structure"
    MACHINE_READABLE = "machine-readable"
    AUTHORITY = "authority"
    FRESHNESS = "freshness"


class Severity(StrEnum):
    """Outcome of a single rule, derived from its score."""

    PASS = "pass"  # noqa: S105
    WARN = "warn"
    FAIL = "fail"

    @classmethod
    def from_score(cls, score: float) -> Severity:
        if score >= 0.999:
            return cls.PASS
        if score > 0.0:
            return cls.WARN
        return cls.FAIL


@dataclass(frozen=True)
class Heading:
    """A heading node (h1-h6)."""

    level: int
    text: str


@dataclass(frozen=True)
class Link:
    """An anchor extracted from the document."""

    href: str
    text: str
    external: bool


@dataclass
class Document:
    """Normalized view of a page, format-agnostic (HTML or Markdown)."""

    title: str = ""
    h1: str = ""
    headings: list[Heading] = field(default_factory=list)
    paragraphs: list[str] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    tables: int = 0
    lists: int = 0
    json_ld: list[dict[str, object]] = field(default_factory=list)
    meta: dict[str, str] = field(default_factory=dict)
    text: str = ""
    has_faq: bool = False
    has_summary: bool = False
    dates: list[str] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    @property
    def external_links(self) -> list[Link]:
        return [link for link in self.links if link.external]


@dataclass(frozen=True)
class RuleResult:
    """Result of evaluating one rule against a document."""

    rule_id: str
    title: str
    category: Category
    weight: float
    score: float  # normalized 0.0 - 1.0
    severity: Severity
    detail: str
    fix: str

    @property
    def passed(self) -> bool:
        return self.severity is Severity.PASS


@dataclass(frozen=True)
class AuditReport:
    """Aggregate audit outcome for a single document."""

    score: int  # 0 - 100
    grade: str  # A - F
    results: list[RuleResult]
    by_category: dict[Category, int]

    @property
    def failed(self) -> list[RuleResult]:
        return [r for r in self.results if r.severity is Severity.FAIL]

    @property
    def warnings(self) -> list[RuleResult]:
        return [r for r in self.results if r.severity is Severity.WARN]
