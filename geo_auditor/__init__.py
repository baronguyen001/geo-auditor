"""geo-auditor: score how likely AI answer engines are to cite your content.

A keyless, offline, deterministic auditor for GEO (Generative Engine
Optimization) and AEO (Answer Engine Optimization). Point it at an HTML or
Markdown page and it scores the page against 14 well-known answer-engine
heuristics, then tells you what to fix.
"""

from geo_auditor.models import (
    AuditReport,
    Category,
    Document,
    Heading,
    Link,
    RuleResult,
    Severity,
)
from geo_auditor.parse import parse_content
from geo_auditor.report import render_json, render_markdown, render_text
from geo_auditor.rules import ALL_RULES, audit
from geo_auditor.score import build_report

__version__ = "0.1.0"

__all__ = [
    "ALL_RULES",
    "AuditReport",
    "Category",
    "Document",
    "Heading",
    "Link",
    "RuleResult",
    "Severity",
    "__version__",
    "audit",
    "build_report",
    "parse_content",
    "render_json",
    "render_markdown",
    "render_text",
]
