"""Diff two JSON audit reports produced by geo-auditor."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class JsonRule:
    """Validated rule data from a JSON report."""

    rule_id: str
    title: str
    score: float


@dataclass(frozen=True)
class JsonAuditReport:
    """Validated subset of a JSON report needed for diffing."""

    score: int
    grade: str
    rules: dict[str, JsonRule]


@dataclass(frozen=True)
class RuleDelta:
    """Per-rule score change between two reports."""

    rule_id: str
    title: str
    before_score: float | None
    after_score: float | None
    delta: float | None
    status: str


@dataclass(frozen=True)
class AuditDiff:
    """Overall and per-rule diff between two audit reports."""

    before_score: int
    after_score: int
    score_delta: int
    before_grade: str
    after_grade: str
    rule_deltas: list[RuleDelta]


def _require_mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object.")
    return value


def _require_str(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string.")
    return value


def _require_score(value: object, label: str) -> float:
    if not isinstance(value, int | float):
        raise ValueError(f"{label} must be a number.")
    return float(value)


def parse_json_report(value: object) -> JsonAuditReport:
    """Validate and normalize a report loaded from ``--format json`` output."""

    payload = _require_mapping(value, "report")
    score_value = payload.get("score")
    if not isinstance(score_value, int):
        raise ValueError("report.score must be an integer.")
    grade = _require_str(payload.get("grade"), "report.grade")
    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError("report.results must be a list.")

    rules: dict[str, JsonRule] = {}
    for index, raw_rule in enumerate(results):
        rule = _require_mapping(raw_rule, f"report.results[{index}]")
        rule_id = _require_str(rule.get("rule_id"), f"report.results[{index}].rule_id")
        title = _require_str(rule.get("title"), f"report.results[{index}].title")
        rules[rule_id] = JsonRule(
            rule_id=rule_id,
            title=title,
            score=_require_score(rule.get("score"), f"report.results[{index}].score"),
        )
    return JsonAuditReport(score=score_value, grade=grade, rules=rules)


def load_json_report(path: Path) -> JsonAuditReport:
    """Load and validate a JSON report from *path*."""

    try:
        text = _read_json_text(path)
        value: Any = json.loads(text)
    except OSError as exc:
        raise ValueError(f"Cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in {path}: {exc.msg}") from exc
    return parse_json_report(value)


def _read_json_text(path: Path) -> str:
    data = path.read_bytes()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("utf-16")


def diff_reports(before: JsonAuditReport, after: JsonAuditReport) -> AuditDiff:
    """Compute an audit diff from two validated reports."""

    rule_ids = sorted(set(before.rules) | set(after.rules))
    deltas: list[RuleDelta] = []
    for rule_id in rule_ids:
        before_rule = before.rules.get(rule_id)
        after_rule = after.rules.get(rule_id)
        if before_rule is None and after_rule is not None:
            deltas.append(
                RuleDelta(
                    rule_id=rule_id,
                    title=after_rule.title,
                    before_score=None,
                    after_score=after_rule.score,
                    delta=None,
                    status="added",
                )
            )
        elif before_rule is not None and after_rule is None:
            deltas.append(
                RuleDelta(
                    rule_id=rule_id,
                    title=before_rule.title,
                    before_score=before_rule.score,
                    after_score=None,
                    delta=None,
                    status="removed",
                )
            )
        elif before_rule is not None and after_rule is not None:
            delta = round(after_rule.score - before_rule.score, 4)
            status = "unchanged"
            if delta < 0:
                status = "regression"
            elif delta > 0:
                status = "improvement"
            deltas.append(
                RuleDelta(
                    rule_id=rule_id,
                    title=after_rule.title,
                    before_score=before_rule.score,
                    after_score=after_rule.score,
                    delta=delta,
                    status=status,
                )
            )
    return AuditDiff(
        before_score=before.score,
        after_score=after.score,
        score_delta=after.score - before.score,
        before_grade=before.grade,
        after_grade=after.grade,
        rule_deltas=sorted(deltas, key=_delta_sort_key),
    )


def diff_report_files(before_path: Path, after_path: Path) -> AuditDiff:
    """Load two JSON reports and return their diff."""

    return diff_reports(load_json_report(before_path), load_json_report(after_path))


def _delta_sort_key(delta: RuleDelta) -> tuple[int, float, str]:
    status_order = {
        "regression": 0,
        "removed": 1,
        "added": 2,
        "improvement": 3,
        "unchanged": 4,
    }
    if delta.delta is None:
        magnitude = 0.0
    elif delta.delta < 0:
        magnitude = delta.delta
    else:
        magnitude = -delta.delta
    return (status_order[delta.status], magnitude, delta.rule_id)


def _format_score(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{int(round(value * 100))}%"


def _format_delta(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value * 100:+.0f}pp"


def render_diff_text(diff: AuditDiff) -> str:
    """Render an audit diff as plain text."""

    lines = [
        "GEO/AEO audit diff",
        "==================",
        f"Score: {diff.before_score}/100 -> {diff.after_score}/100 ({diff.score_delta:+d})",
        f"Grade: {diff.before_grade} -> {diff.after_grade}",
        "",
        "Rule changes (worst regressions first):",
    ]
    for delta in diff.rule_deltas:
        lines.append(
            "  "
            f"[{delta.status.upper()}] {delta.title} ({delta.rule_id}) "
            f"{_format_score(delta.before_score)} -> {_format_score(delta.after_score)} "
            f"({_format_delta(delta.delta)})"
        )
    return "\n".join(lines)


def render_diff_json(diff: AuditDiff) -> str:
    """Render an audit diff as JSON."""

    payload = {
        "before_score": diff.before_score,
        "after_score": diff.after_score,
        "score_delta": diff.score_delta,
        "before_grade": diff.before_grade,
        "after_grade": diff.after_grade,
        "rule_deltas": [
            {
                "rule_id": delta.rule_id,
                "title": delta.title,
                "before_score": delta.before_score,
                "after_score": delta.after_score,
                "delta": delta.delta,
                "status": delta.status,
            }
            for delta in diff.rule_deltas
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=True)


def render_diff_markdown(diff: AuditDiff) -> str:
    """Render an audit diff as Markdown."""

    lines = [
        "# GEO/AEO audit diff",
        "",
        f"**Score:** {diff.before_score}/100 -> {diff.after_score}/100 ({diff.score_delta:+d})",
        "",
        f"**Grade:** {diff.before_grade} -> {diff.after_grade}",
        "",
        "| Status | Rule | Before | After | Delta |",
        "| --- | --- | --- | --- | --- |",
    ]
    for delta in diff.rule_deltas:
        lines.append(
            f"| {delta.status.upper()} | {delta.title} | "
            f"{_format_score(delta.before_score)} | {_format_score(delta.after_score)} | "
            f"{_format_delta(delta.delta)} |"
        )
    return "\n".join(lines)
