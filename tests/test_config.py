"""Tests for .geo-audit.toml configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from geo_auditor.config import apply_config, load_config
from geo_auditor.rules import ALL_RULES


def test_missing_config_is_empty(tmp_path: Path) -> None:
    config = load_config(tmp_path / "missing.toml")
    assert config.weights == {}
    assert config.disabled == frozenset()
    assert config.defaults.min_score is None


def test_load_explicit_config(tmp_path: Path) -> None:
    path = tmp_path / "geo.toml"
    path.write_text(
        """
        [rules]
        weights = { answer-first = 4.5 }
        disabled = ["faq"]

        [defaults]
        min_score = 80
        """,
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.weights == {"answer-first": 4.5}
    assert config.disabled == frozenset({"faq"})
    assert config.defaults.min_score == 80


def test_auto_discovers_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".geo-audit.toml").write_text(
        """
        [rules]
        disabled = ["canonical"]
        """,
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    config = load_config(None)
    assert config.disabled == frozenset({"canonical"})


def test_config_validation_errors(tmp_path: Path) -> None:
    unknown = tmp_path / "unknown.toml"
    unknown.write_text('[rules]\ndisabled = ["missing-rule"]\n', encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown rule id"):
        load_config(unknown)

    bad_weight = tmp_path / "bad-weight.toml"
    bad_weight.write_text("[rules]\nweights = { answer-first = 0 }\n", encoding="utf-8")
    with pytest.raises(ValueError, match="> 0"):
        load_config(bad_weight)


def test_apply_config_reweights_and_disables() -> None:
    config = load_config(Path("does-not-exist.toml"))
    rules = apply_config(ALL_RULES, config)
    assert len(rules) == len(ALL_RULES)

    explicit = type(config)(
        weights={"answer-first": 9.0},
        disabled=frozenset({"faq"}),
        defaults=config.defaults,
    )
    effective = apply_config(ALL_RULES, explicit)
    ids = [rule.id for rule in effective]
    assert "faq" not in ids
    answer_first = next(rule for rule in effective if rule.id == "answer-first")
    original = next(rule for rule in ALL_RULES if rule.id == "answer-first")
    assert answer_first.weight == 9.0
    assert original.weight == 3.0
