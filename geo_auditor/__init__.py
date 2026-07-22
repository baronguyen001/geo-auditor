"""geo-auditor: score how likely AI answer engines are to cite your content.

A keyless, offline, deterministic auditor for GEO (Generative Engine
Optimization) and AEO (Answer Engine Optimization). Point it at an HTML or
Markdown page and it scores the page against 21 well-known answer-engine
heuristics, then tells you what to fix.
"""

from geo_auditor.batch import BatchReport, BatchRuleSummary, FileAudit, scan_paths
from geo_auditor.config import GeoAuditConfig, apply_config, load_config
from geo_auditor.diff import (
    AuditDiff,
    RuleDelta,
    diff_report_files,
    diff_reports,
    render_diff_json,
    render_diff_markdown,
    render_diff_text,
)
from geo_auditor.models import (
    AuditReport,
    Category,
    Document,
    Heading,
    Image,
    Link,
    RuleResult,
    Severity,
)
from geo_auditor.parse import parse_content
from geo_auditor.remediate import (
    RemediationItem,
    RemediationPlan,
    build_remediation,
    render_remediation_json,
    render_remediation_markdown,
    render_remediation_text,
)
from geo_auditor.report import (
    render_batch_html,
    render_batch_json,
    render_batch_markdown,
    render_batch_text,
    render_diff_html,
    render_html,
    render_json,
    render_markdown,
    render_remediation_html,
    render_text,
)
from geo_auditor.rules import ALL_RULES, audit
from geo_auditor.score import build_report

__version__ = "0.4.0"

__all__ = [
    "ALL_RULES",
    "AuditDiff",
    "AuditReport",
    "BatchReport",
    "BatchRuleSummary",
    "Category",
    "Document",
    "FileAudit",
    "GeoAuditConfig",
    "Heading",
    "Image",
    "Link",
    "RemediationItem",
    "RemediationPlan",
    "RuleDelta",
    "RuleResult",
    "Severity",
    "__version__",
    "apply_config",
    "audit",
    "build_remediation",
    "build_report",
    "diff_report_files",
    "diff_reports",
    "load_config",
    "parse_content",
    "render_diff_json",
    "render_diff_markdown",
    "render_diff_text",
    "render_batch_html",
    "render_batch_json",
    "render_batch_markdown",
    "render_batch_text",
    "render_diff_html",
    "render_html",
    "render_json",
    "render_markdown",
    "render_remediation_html",
    "render_remediation_json",
    "render_remediation_markdown",
    "render_remediation_text",
    "render_text",
    "scan_paths",
]
