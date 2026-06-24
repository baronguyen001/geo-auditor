"""Tests for the command-line interface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from geo_auditor.cli import main


def test_check_text(capsys: pytest.CaptureFixture[str], fixtures_dir: Path) -> None:
    code = main(["check", str(fixtures_dir / "strong_page.html")])
    out = capsys.readouterr().out
    assert code == 0
    assert "Score:" in out
    assert "grade A" in out or "grade B" in out


def test_check_json(capsys: pytest.CaptureFixture[str], fixtures_dir: Path) -> None:
    code = main(["check", str(fixtures_dir / "strong_page.html"), "--format", "json"])
    out = capsys.readouterr().out
    assert code == 0
    data = json.loads(out)
    assert data["score"] >= 80


def test_check_markdown_format(capsys: pytest.CaptureFixture[str], fixtures_dir: Path) -> None:
    code = main(["check", str(fixtures_dir / "weak_page.md"), "--format", "md"])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("# GEO/AEO readiness report")


def test_rules_command(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["rules"])
    out = capsys.readouterr().out
    assert code == 0
    assert "answer-first" in out
    assert "freshness-signal" in out


def test_init_llms(capsys: pytest.CaptureFixture[str], fixtures_dir: Path) -> None:
    code = main(["init-llms", str(fixtures_dir / "strong_page.html")])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("# How to Brew")


def test_min_score_gate_fails(capsys: pytest.CaptureFixture[str], fixtures_dir: Path) -> None:
    code = main(["check", str(fixtures_dir / "weak_page.md"), "--min-score", "90"])
    err = capsys.readouterr().err
    assert code == 1
    assert "FAILED" in err


def test_min_score_gate_passes(fixtures_dir: Path) -> None:
    code = main(["check", str(fixtures_dir / "strong_page.html"), "--min-score", "50"])
    assert code == 0


def test_missing_file(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["check", "does_not_exist.html"])
    err = capsys.readouterr().err
    assert code == 2
    assert "error" in err


def test_url_in_offline_mode_is_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["check", "https://example.com", "--offline"])
    err = capsys.readouterr().err
    assert code == 2
    assert "offline" in err.lower()


def test_init_llms_missing_file(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["init-llms", "nope.md"])
    assert code == 2
    assert "error" in capsys.readouterr().err


def test_explicit_format_in(capsys: pytest.CaptureFixture[str], fixtures_dir: Path) -> None:
    code = main(["check", str(fixtures_dir / "weak_page.md"), "--format-in", "markdown"])
    assert code == 0


def test_version_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0


def test_no_command_errors() -> None:
    with pytest.raises(SystemExit):
        main([])
