"""Tests for local corpus scanning."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from geo_auditor.batch import discover_files, scan_paths
from geo_auditor.report import (
    render_batch_html,
    render_batch_json,
    render_batch_markdown,
    render_batch_text,
)


def _is_ascii(text: str) -> bool:
    return all(ord(ch) < 128 for ch in text)


def test_discover_files_recurses_and_sorts(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    first = nested / "b.md"
    second = tmp_path / "a.html"
    ignored = nested / "ignore.txt"
    first.write_text("# B", encoding="utf-8")
    second.write_text("<h1>A</h1>", encoding="utf-8")
    ignored.write_text("ignored", encoding="utf-8")

    assert discover_files([str(tmp_path)]) == sorted([second, first], key=lambda p: p.as_posix())


def test_discover_files_rejects_urls() -> None:
    with pytest.raises(ValueError, match="URLs"):
        discover_files(["https://example.com/page"])


def test_scan_paths_builds_corpus_report(fixtures_dir: Path) -> None:
    report = scan_paths([str(fixtures_dir)])
    assert len(report.files) == 2
    assert report.average_score > 0
    assert sum(report.count_by_grade.values()) == 2
    assert report.files[0].score <= report.files[1].score
    assert report.worst_rules
    assert report.files[0].top_failing_rule is not None


def test_scan_paths_no_matches(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("nothing", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="No matching"):
        scan_paths([str(tmp_path)])


def test_batch_renderers_are_ascii(fixtures_dir: Path) -> None:
    report = scan_paths([str(fixtures_dir)])
    text = render_batch_text(report)
    markdown = render_batch_markdown(report)
    html = render_batch_html(report)
    json_text = render_batch_json(report)

    assert _is_ascii(text)
    assert _is_ascii(markdown)
    assert _is_ascii(html)
    assert _is_ascii(json_text)
    assert "Leaderboard" in text
    assert markdown.startswith("# GEO/AEO batch scan")
    assert html.startswith("<!doctype html>")
    assert json.loads(json_text)["average_score"] == report.average_score
