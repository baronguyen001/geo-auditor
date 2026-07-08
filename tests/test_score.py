"""Tests for scoring and report aggregation."""

from __future__ import annotations

from geo_auditor.models import Category, Document
from geo_auditor.score import build_report, grade_for


def test_grade_bands() -> None:
    assert grade_for(95) == "A"
    assert grade_for(85) == "B"
    assert grade_for(75) == "C"
    assert grade_for(65) == "D"
    assert grade_for(10) == "F"


def test_strong_scores_high(strong_doc: Document) -> None:
    report = build_report(strong_doc)
    assert report.score >= 80
    assert report.grade in {"A", "B"}
    assert set(report.by_category) == set(Category)


def test_weak_scores_low(weak_doc: Document) -> None:
    report = build_report(weak_doc)
    assert report.score <= 45
    assert report.grade in {"D", "F"}


def test_strong_beats_weak(strong_doc: Document, weak_doc: Document) -> None:
    assert build_report(strong_doc).score > build_report(weak_doc).score


def test_empty_document_scores_zero() -> None:
    report = build_report(Document())
    assert report.score == 0
    assert report.grade == "F"


def test_by_category_only_includes_used_categories() -> None:
    from geo_auditor.rules.structure import ContentDepthRule

    report = build_report(Document(text="w " * 400), rules=[ContentDepthRule()])
    assert set(report.by_category) == {Category.STRUCTURE}
    assert report.score == 100


def test_report_failed_and_warnings_helpers(weak_doc: Document) -> None:
    report = build_report(weak_doc)
    assert report.failed
    assert len(report.results) == 18
