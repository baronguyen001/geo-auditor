"""Batch scanning helpers for local content folders."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from geo_auditor.models import RuleResult, Severity
from geo_auditor.parse import parse_content
from geo_auditor.rules import ALL_RULES
from geo_auditor.rules.base import Rule
from geo_auditor.score import build_report, grade_for

_SUPPORTED_SUFFIXES = frozenset({".html", ".htm", ".md", ".markdown"})


@dataclass(frozen=True)
class FileAudit:
    """Audit summary for one local file."""

    path: str
    score: int
    grade: str
    top_failing_rule: RuleResult | None


@dataclass(frozen=True)
class BatchRuleSummary:
    """Corpus-level summary for one rule."""

    rule_id: str
    title: str
    fail_count: int
    affected_count: int
    weighted_loss: float


@dataclass(frozen=True)
class BatchReport:
    """Aggregate audit outcome for a local corpus."""

    files: list[FileAudit]
    average_score: int
    average_grade: str
    count_by_grade: dict[str, int]
    worst_rules: list[BatchRuleSummary]


def _is_urlish(value: str) -> bool:
    return "://" in value


def _supported_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in _SUPPORTED_SUFFIXES


def discover_files(paths: list[str]) -> list[Path]:
    """Return supported local files from *paths* in deterministic order."""

    found: list[Path] = []
    for raw in paths:
        if _is_urlish(raw):
            raise ValueError(
                "scan only accepts local files and directories; URLs are out of scope."
            )
        path = Path(raw)
        if path.is_dir():
            found.extend(
                child
                for child in path.rglob("*")
                if child.is_file() and child.suffix.lower() in _SUPPORTED_SUFFIXES
            )
        elif _supported_file(path):
            found.append(path)
    return sorted(found, key=lambda item: item.as_posix().lower())


def _top_failing_rule(results: list[RuleResult]) -> RuleResult | None:
    order = {Severity.FAIL: 0, Severity.WARN: 1, Severity.PASS: 2}
    for result in sorted(results, key=lambda r: (order[r.severity], -r.weight, r.rule_id)):
        if result.severity is not Severity.PASS:
            return result
    return None


def _summarize_rules(results_by_file: list[list[RuleResult]]) -> list[BatchRuleSummary]:
    by_rule: dict[str, BatchRuleSummary] = {}
    for results in results_by_file:
        for result in results:
            previous = by_rule.get(result.rule_id)
            fail_count = 1 if result.severity is Severity.FAIL else 0
            affected_count = 1 if result.severity is not Severity.PASS else 0
            weighted_loss = result.weight * (1.0 - result.score)
            if previous is None:
                by_rule[result.rule_id] = BatchRuleSummary(
                    rule_id=result.rule_id,
                    title=result.title,
                    fail_count=fail_count,
                    affected_count=affected_count,
                    weighted_loss=weighted_loss,
                )
            else:
                by_rule[result.rule_id] = BatchRuleSummary(
                    rule_id=result.rule_id,
                    title=result.title,
                    fail_count=previous.fail_count + fail_count,
                    affected_count=previous.affected_count + affected_count,
                    weighted_loss=previous.weighted_loss + weighted_loss,
                )
    return sorted(
        by_rule.values(),
        key=lambda item: (
            -item.weighted_loss,
            -item.fail_count,
            -item.affected_count,
            item.rule_id,
        ),
    )


def scan_paths(paths: list[str], rules: Sequence[Rule] = ALL_RULES) -> BatchReport:
    """Audit every supported local file under *paths* and return a batch report."""

    files = discover_files(paths)
    if not files:
        raise FileNotFoundError("No matching HTML or Markdown files found.")

    file_results: list[FileAudit] = []
    results_by_file: list[list[RuleResult]] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        doc = parse_content(text, fmt="auto")
        report = build_report(doc, rules=rules)
        results_by_file.append(report.results)
        file_results.append(
            FileAudit(
                path=path.as_posix(),
                score=report.score,
                grade=report.grade,
                top_failing_rule=_top_failing_rule(report.results),
            )
        )

    average_score = round(sum(item.score for item in file_results) / len(file_results))
    counts = dict.fromkeys(("A", "B", "C", "D", "F"), 0)
    for item in file_results:
        counts[item.grade] += 1
    return BatchReport(
        files=sorted(file_results, key=lambda item: (item.score, item.grade, item.path.lower())),
        average_score=average_score,
        average_grade=grade_for(average_score),
        count_by_grade=counts,
        worst_rules=_summarize_rules(results_by_file),
    )
