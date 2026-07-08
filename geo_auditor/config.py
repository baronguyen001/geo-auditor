"""Configuration loading and effective rule-set construction."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, cast

from geo_auditor.models import Category, Document, RuleResult
from geo_auditor.rules import ALL_RULES
from geo_auditor.rules.base import Rule


@dataclass(frozen=True)
class DefaultsConfig:
    """Default CLI options loaded from configuration."""

    min_score: int | None = None


@dataclass(frozen=True)
class GeoAuditConfig:
    """Validated ``.geo-audit.toml`` settings."""

    weights: dict[str, float]
    disabled: frozenset[str]
    defaults: DefaultsConfig


@dataclass(frozen=True)
class WeightedRule:
    """Rule wrapper that changes weight without mutating the original rule."""

    rule: Rule
    weight: float

    @property
    def id(self) -> str:
        return self.rule.id

    @property
    def title(self) -> str:
        return self.rule.title

    @property
    def category(self) -> Category:
        return self.rule.category

    def check(self, doc: Document) -> RuleResult:
        result = self.rule.check(doc)
        return replace(result, weight=self.weight)


EMPTY_CONFIG = GeoAuditConfig(weights={}, disabled=frozenset(), defaults=DefaultsConfig())


def load_config(path: str | Path | None) -> GeoAuditConfig:
    """Load and validate configuration from *path* or ``.geo-audit.toml``."""

    config_path = Path(path) if path is not None else Path.cwd() / ".geo-audit.toml"
    if not config_path.is_file():
        return EMPTY_CONFIG
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)
    return _parse_config(raw)


def apply_config(rules: Sequence[Rule], config: GeoAuditConfig) -> tuple[Rule, ...]:
    """Return a new rule tuple with disabled rules removed and weights applied."""

    effective: list[Rule] = []
    for rule in rules:
        if rule.id in config.disabled:
            continue
        weight = config.weights.get(rule.id)
        if weight is None:
            effective.append(rule)
        else:
            effective.append(cast(Rule, WeightedRule(rule=rule, weight=weight)))
    return tuple(effective)


def _parse_config(raw: Mapping[str, Any]) -> GeoAuditConfig:
    known = {rule.id for rule in ALL_RULES}
    rules_table = _mapping(raw.get("rules", {}), "rules")
    defaults_table = _mapping(raw.get("defaults", {}), "defaults")

    weights = _parse_weights(rules_table.get("weights", {}), known)
    disabled = _parse_disabled(rules_table.get("disabled", []), known)
    defaults = DefaultsConfig(min_score=_parse_min_score(defaults_table.get("min_score")))
    return GeoAuditConfig(weights=weights, disabled=disabled, defaults=defaults)


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    raise ValueError(f"[{name}] must be a TOML table.")


def _parse_weights(value: object, known: set[str]) -> dict[str, float]:
    if not isinstance(value, Mapping):
        raise ValueError("[rules].weights must be a TOML inline table.")
    weights: dict[str, float] = {}
    for raw_rule_id, raw_weight in value.items():
        if not isinstance(raw_rule_id, str):
            raise ValueError("Rule ids in [rules].weights must be strings.")
        if raw_rule_id not in known:
            raise ValueError(f"Unknown rule id in weights: {raw_rule_id}")
        if isinstance(raw_weight, bool) or not isinstance(raw_weight, int | float):
            raise ValueError(f"Weight for {raw_rule_id} must be a number.")
        weight = float(raw_weight)
        if weight <= 0:
            raise ValueError(f"Weight for {raw_rule_id} must be > 0.")
        weights[raw_rule_id] = weight
    return weights


def _parse_disabled(value: object, known: set[str]) -> frozenset[str]:
    if not isinstance(value, list):
        raise ValueError("[rules].disabled must be a list of rule ids.")
    disabled: set[str] = set()
    for raw_rule_id in value:
        if not isinstance(raw_rule_id, str):
            raise ValueError("Disabled rule ids must be strings.")
        if raw_rule_id not in known:
            raise ValueError(f"Unknown rule id in disabled: {raw_rule_id}")
        disabled.add(raw_rule_id)
    return frozenset(disabled)


def _parse_min_score(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("[defaults].min_score must be an integer.")
    if not 0 <= value <= 100:
        raise ValueError("[defaults].min_score must be between 0 and 100.")
    return value
