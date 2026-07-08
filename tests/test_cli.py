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


def test_check_html_format(capsys: pytest.CaptureFixture[str], fixtures_dir: Path) -> None:
    code = main(["check", str(fixtures_dir / "strong_page.html"), "--format", "html"])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("<!doctype html>")
    assert "GEO/AEO readiness report" in out


def test_scan_markdown(capsys: pytest.CaptureFixture[str], fixtures_dir: Path) -> None:
    code = main(["scan", str(fixtures_dir), "--format", "md"])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("# GEO/AEO batch scan")
    assert "Leaderboard" in out


def test_scan_html(capsys: pytest.CaptureFixture[str], fixtures_dir: Path) -> None:
    code = main(["scan", str(fixtures_dir), "--format", "html"])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("<!doctype html>")
    assert "GEO/AEO batch scan" in out


def test_scan_honors_config(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    fixtures_dir: Path,
) -> None:
    config = tmp_path / ".geo-audit.toml"
    config.write_text('[rules]\ndisabled = ["answer-first"]\n', encoding="utf-8")
    code = main(["scan", "--config", str(config), str(fixtures_dir), "--format", "json"])
    out = capsys.readouterr().out
    assert code == 0
    assert "answer-first" not in out


def test_scan_min_score_gate_fails(capsys: pytest.CaptureFixture[str], fixtures_dir: Path) -> None:
    code = main(["scan", str(fixtures_dir), "--min-score", "100"])
    err = capsys.readouterr().err
    assert code == 1
    assert "corpus average" in err


def test_scan_no_matching_files(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")
    code = main(["scan", str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 2
    assert "No matching" in err


def test_scan_rejects_urls(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["scan", "https://example.com"])
    err = capsys.readouterr().err
    assert code == 2
    assert "URLs" in err


def test_diff_command(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    fixtures_dir: Path,
) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    main(["check", str(fixtures_dir / "strong_page.html"), "--format", "json"])
    before.write_text(capsys.readouterr().out, encoding="utf-8")
    main(["check", str(fixtures_dir / "weak_page.md"), "--format", "json"])
    after.write_text(capsys.readouterr().out, encoding="utf-8")

    code = main(["diff", str(before), str(after)])
    out = capsys.readouterr().out
    assert code == 0
    assert "GEO/AEO audit diff" in out
    assert "REGRESSION" in out


def test_diff_json_format(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text(
        json.dumps(
            {
                "score": 0,
                "grade": "F",
                "results": [{"rule_id": "a", "title": "A", "score": 0}],
            }
        ),
        encoding="utf-8",
    )
    after.write_text(
        json.dumps(
            {"score": 100, "grade": "A", "results": [{"rule_id": "a", "title": "A", "score": 1}]}
        ),
        encoding="utf-8",
    )
    code = main(["diff", str(before), str(after), "--format", "json"])
    out = capsys.readouterr().out
    assert code == 0
    assert json.loads(out)["score_delta"] == 100


def test_diff_malformed_json(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    before.write_text("{bad", encoding="utf-8")
    after.write_text("{}", encoding="utf-8")
    code = main(["diff", str(before), str(after)])
    err = capsys.readouterr().err
    assert code == 2
    assert "Malformed JSON" in err


def test_rules_command(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["rules"])
    out = capsys.readouterr().out
    assert code == 0
    assert "answer-first" in out
    assert "freshness-signal" in out
    assert "alt-text" in out


def test_rules_command_honors_config(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    config = tmp_path / ".geo-audit.toml"
    config.write_text(
        '[rules]\nweights = { answer-first = 5 }\ndisabled = ["faq"]\n',
        encoding="utf-8",
    )
    code = main(["rules", "--config", str(config)])
    out = capsys.readouterr().out
    assert code == 0
    assert "answer-first" in out
    assert "w=5.0" in out
    assert "faq" not in out


def test_check_honors_config_defaults(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    fixtures_dir: Path,
) -> None:
    config = tmp_path / ".geo-audit.toml"
    config.write_text("[defaults]\nmin_score = 80\n", encoding="utf-8")
    code = main(["check", "--config", str(config), str(fixtures_dir / "weak_page.md")])
    err = capsys.readouterr().err
    assert code == 1
    assert "below --min-score 80" in err


def test_check_explicit_min_score_overrides_config(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    fixtures_dir: Path,
) -> None:
    config = tmp_path / ".geo-audit.toml"
    config.write_text("[defaults]\nmin_score = 100\n", encoding="utf-8")
    code = main(
        [
            "check",
            "--config",
            str(config),
            str(fixtures_dir / "weak_page.md"),
            "--min-score",
            "0",
        ]
    )
    assert code == 0
    capsys.readouterr()


def test_fix_json_top(capsys: pytest.CaptureFixture[str], fixtures_dir: Path) -> None:
    code = main(["fix", str(fixtures_dir / "weak_page.md"), "--format", "json", "--top", "2"])
    out = capsys.readouterr().out
    assert code == 0
    data = json.loads(out)
    assert len(data["items"]) == 2
    assert data["total_recoverable_points"] > 0


def test_fix_markdown(capsys: pytest.CaptureFixture[str], fixtures_dir: Path) -> None:
    code = main(["fix", str(fixtures_dir / "weak_page.md"), "--format", "md"])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("# GEO/AEO remediation plan")


def test_fix_honors_config(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    fixtures_dir: Path,
) -> None:
    config = tmp_path / ".geo-audit.toml"
    config.write_text('[rules]\ndisabled = ["answer-first"]\n', encoding="utf-8")
    code = main(["fix", "--config", str(config), str(fixtures_dir / "weak_page.md")])
    out = capsys.readouterr().out
    assert code == 0
    assert "answer-first" not in out


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
