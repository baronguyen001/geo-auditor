# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
