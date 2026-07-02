"""Tests for JSON audit diffs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from geo_auditor.diff import (
    diff_report_files,
    diff_reports,
    load_json_report,
    parse_json_report,
    render_diff_json,
    render_diff_markdown,
    render_diff_text,
)
from geo_auditor.models import Document
from geo_auditor.report import render_json
from geo_auditor.score import build_report


def _is_ascii(text: str) -> bool:
    return all(ord(ch) < 128 for ch in text)


def _payload(score: int, grade: str, rules: list[dict[str, object]]) -> dict[str, object]:
    return {"score": score, "grade": grade, "by_category": {}, "results": rules}


def test_diff_reports_flags_regressions_improvements_added_removed() -> None:
    before = parse_json_report(
        _payload(
            80,
            "B",
            [
                {"rule_id": "a", "title": "A", "score": 1.0},
                {"rule_id": "b", "title": "B", "score": 0.0},
                {"rule_id": "removed", "title": "Removed", "score": 1.0},
            ],
        )
    )
    after = parse_json_report(
        _payload(
            70,
            "C",
            [
                {"rule_id": "a", "title": "A", "score": 0.0},
                {"rule_id": "b", "title": "B", "score": 1.0},
                {"rule_id": "added", "title": "Added", "score": 1.0},
            ],
        )
    )

    diff = diff_reports(before, after)

    assert diff.score_delta == -10
    assert [item.status for item in diff.rule_deltas] == [
        "regression",
        "removed",
        "added",
        "improvement",
    ]


def test_load_json_report_and_diff_files(
    tmp_path: Path,
    strong_doc: Document,
    weak_doc: Document,
) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text(render_json(build_report(strong_doc)), encoding="utf-8")
    after.write_text(render_json(build_report(weak_doc)), encoding="utf-8")

    loaded = load_json_report(before)
    diff = diff_report_files(before, after)

    assert loaded.score >= 80
    assert diff.after_score < diff.before_score
    assert any(item.status == "regression" for item in diff.rule_deltas)


def test_render_diff_formats_are_ascii() -> None:
    before = parse_json_report(_payload(50, "F", [{"rule_id": "a", "title": "A", "score": 0.0}]))
    after = parse_json_report(_payload(100, "A", [{"rule_id": "a", "title": "A", "score": 1.0}]))
    diff = diff_reports(before, after)

    text = render_diff_text(diff)
    markdown = render_diff_markdown(diff)
    json_text = render_diff_json(diff)

    assert _is_ascii(text)
    assert _is_ascii(markdown)
    assert _is_ascii(json_text)
    assert "IMPROVEMENT" in text
    assert markdown.startswith("# GEO/AEO audit diff")
    assert json.loads(json_text)["score_delta"] == 50


def test_parse_json_report_rejects_malformed_shape() -> None:
    with pytest.raises(ValueError, match="score"):
        parse_json_report({"score": "bad", "grade": "F", "results": []})


def test_load_json_report_rejects_bad_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{bad", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed JSON"):
        load_json_report(path)
