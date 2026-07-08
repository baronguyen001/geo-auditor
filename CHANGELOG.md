# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-07-08

### Added
- `geo-audit fix <path|url>` builds a prioritized remediation plan with
  projected point gains in text, Markdown, or JSON.
- `.geo-audit.toml` config supports rule weight overrides, disabled rules, and
  a default `min_score`, with `--config PATH` for explicit selection.
- A multimedia pillar adds `alt-text`, `table-data`, `canonical`, and
  `social-card` rules, raising the built-in rule count from 14 to 18.

## [0.2.0] - 2026-07-02

### Added
- `geo-audit scan <paths...>` audits local content folders, reports a corpus
  average, and gates CI on the average score with `--min-score`.
- HTML output for `geo-audit check --format html` and
  `geo-audit scan --format html`.
- `geo-audit diff <before.json> <after.json>` compares JSON reports and
  highlights regressions, improvements, added rules, and removed rules.

## [0.1.0] - 2026-06-24

### Added
- Initial release.
- `geo-audit check <path|url>` scores a page against 14 GEO/AEO heuristics
  across four pillars (structure, machine-readable, authority, freshness).
- `geo-audit rules` lists every rule with its category and weight.
- `geo-audit init-llms <path>` generates a starter `llms.txt`.
- Text, JSON, and Markdown report formats.
- `--min-score` flag for use as a CI gate.
- Library API: `parse_content`, `build_report`, `render_text`/`render_json`/
  `render_markdown`.
