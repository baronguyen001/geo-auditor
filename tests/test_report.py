"""Tests for the text/JSON/Markdown renderers."""

from __future__ import annotations

import json

from geo_auditor.models import AuditReport, Category, Document, RuleResult, Severity
from geo_auditor.report import render_html, render_json, render_markdown, render_text
from geo_auditor.score import build_report


def _is_ascii(text: str) -> bool:
    return all(ord(ch) < 128 for ch in text)


def test_render_text_is_ascii_and_has_score(strong_doc: Document) -> None:
    out = render_text(build_report(strong_doc))
    assert _is_ascii(out)
    assert "Score:" in out
    assert "By category" in out
    assert "PASS" in out


def test_render_json_is_valid_and_ascii(strong_doc: Document) -> None:
    out = render_json(build_report(strong_doc))
    assert _is_ascii(out)
    data = json.loads(out)
    assert data["grade"] in {"A", "B"}
    assert len(data["results"]) == 18
    assert "by_category" in data
    assert "multimedia" in data["by_category"]


def test_render_markdown(strong_doc: Document) -> None:
    out = render_markdown(build_report(strong_doc))
    assert _is_ascii(out)
    assert out.startswith("# GEO/AEO readiness report")
    assert "| Category | Score |" in out


def test_render_html_is_static_ascii_and_escaped() -> None:
    report = AuditReport(
        score=0,
        grade="F",
        by_category={Category.STRUCTURE: 0},
        results=[
            RuleResult(
                rule_id="unsafe",
                title="<Title>",
                category=Category.STRUCTURE,
                weight=1.0,
                score=0.0,
                severity=Severity.FAIL,
                detail="<script>bad()</script>",
                fix="Use <strong>text</strong>.",
            )
        ],
    )
    out = render_html(report)
    assert _is_ascii(out)
    assert out.startswith("<!doctype html>")
    assert "<style>" in out
    assert "<script>" not in out
    assert "&lt;script&gt;" in out
    assert "GEO/AEO readiness report" in out


def test_results_sorted_worst_first(weak_doc: Document) -> None:
    report = build_report(weak_doc)
    out = render_text(report)
    first_fail = out.index("[FAIL]")
    pass_index = out.find("[PASS]")
    if pass_index != -1:
        assert first_fail < pass_index
