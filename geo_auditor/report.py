"""Render an :class:`AuditReport` as text, JSON, or Markdown.

All output is ASCII-only on purpose: decorative Unicode (arrows, em dashes)
crashes on Windows cp1252 consoles, which would turn the CI matrix red.
"""

from __future__ import annotations

import html
import json

from geo_auditor.batch import BatchReport
from geo_auditor.models import AuditReport, RuleResult, Severity

_SEVERITY_TAG = {
    Severity.PASS: "PASS",
    Severity.WARN: "WARN",
    Severity.FAIL: "FAIL",
}


def _sorted_results(report: AuditReport) -> list[RuleResult]:
    # Worst first so the most impactful fixes are read first; stable within a
    # severity by descending weight then rule id.
    order = {Severity.FAIL: 0, Severity.WARN: 1, Severity.PASS: 2}
    return sorted(
        report.results,
        key=lambda r: (order[r.severity], -r.weight, r.rule_id),
    )


def _escape(value: object) -> str:
    escaped = html.escape(str(value), quote=True)
    return escaped.encode("ascii", "xmlcharrefreplace").decode("ascii")


def _bar(value: int) -> str:
    return f'<div class="bar" aria-label="{value}/100"><span style="width: {value}%"></span></div>'


def render_text(report: AuditReport) -> str:
    lines = [
        "GEO/AEO readiness report",
        "========================",
        f"Score: {report.score}/100  (grade {report.grade})",
        "",
        "By category:",
    ]
    for category, value in report.by_category.items():
        lines.append(f"  {category.value:<16} {value:>3}/100")
    lines.append("")
    lines.append("Checks (worst first):")
    for r in _sorted_results(report):
        tag = _SEVERITY_TAG[r.severity]
        lines.append(f"  [{tag}] {r.title} ({r.rule_id}) - {int(r.score * 100)}%")
        lines.append(f"        {r.detail}")
        if r.fix:
            lines.append(f"        fix: {r.fix}")
    return "\n".join(lines)


def render_json(report: AuditReport) -> str:
    payload = {
        "score": report.score,
        "grade": report.grade,
        "by_category": {c.value: v for c, v in report.by_category.items()},
        "results": [
            {
                "rule_id": r.rule_id,
                "title": r.title,
                "category": r.category.value,
                "weight": r.weight,
                "score": round(r.score, 4),
                "severity": r.severity.value,
                "detail": r.detail,
                "fix": r.fix,
            }
            for r in report.results
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=True)


def render_markdown(report: AuditReport) -> str:
    lines = [
        "# GEO/AEO readiness report",
        "",
        f"**Score: {report.score}/100** (grade {report.grade})",
        "",
        "| Category | Score |",
        "| --- | --- |",
    ]
    for category, value in report.by_category.items():
        lines.append(f"| {category.value} | {value}/100 |")
    lines.append("")
    lines.append("| Result | Check | Score | Detail | Fix |")
    lines.append("| --- | --- | --- | --- | --- |")
    for r in _sorted_results(report):
        tag = _SEVERITY_TAG[r.severity]
        fix = r.fix or "-"
        lines.append(f"| {tag} | {r.title} | {int(r.score * 100)}% | {r.detail} | {fix} |")
    return "\n".join(lines)


def render_html(report: AuditReport) -> str:
    rows = []
    for result in _sorted_results(report):
        rows.append(
            "<tr>"
            f'<td><span class="status status-{_escape(result.severity.value)}">'
            f"{_escape(_SEVERITY_TAG[result.severity])}</span></td>"
            f"<td>{_escape(result.title)}<br><small>{_escape(result.rule_id)}</small></td>"
            f"<td>{int(result.score * 100)}%</td>"
            f"<td>{_escape(result.detail)}</td>"
            f"<td>{_escape(result.fix or '-')}</td>"
            "</tr>"
        )
    category_rows = []
    for category, value in report.by_category.items():
        category_rows.append(
            f"<tr><th>{_escape(category.value)}</th><td>{_bar(value)}</td><td>{value}/100</td></tr>"
        )
    return _html_page(
        "GEO/AEO readiness report",
        f"""
<section class="summary">
  <div>
    <p class="label">Overall score</p>
    <p class="score">{report.score}<span>/100</span></p>
  </div>
  <div class="grade grade-{_escape(report.grade.lower())}">{_escape(report.grade)}</div>
</section>
<section>
  <h2>By category</h2>
  <table class="category-table">
    <tbody>
      {"".join(category_rows)}
    </tbody>
  </table>
</section>
<section>
  <h2>Checks</h2>
  <table>
    <thead>
      <tr><th>Status</th><th>Check</th><th>Score</th><th>Detail</th><th>Fix</th></tr>
    </thead>
    <tbody>
      {"".join(rows)}
    </tbody>
  </table>
</section>
""",
    )


def render_batch_text(report: BatchReport) -> str:
    lines = [
        "GEO/AEO batch scan",
        "==================",
        f"Files: {len(report.files)}",
        f"Average score: {report.average_score}/100  (grade {report.average_grade})",
        "By grade: "
        + " ".join(f"{grade}={count}" for grade, count in report.count_by_grade.items()),
        "",
        "Leaderboard (worst first):",
        "  Score Grade Top issue             Path",
    ]
    for item in report.files:
        top = item.top_failing_rule.rule_id if item.top_failing_rule else "none"
        lines.append(f"  {item.score:>5} {item.grade:<5} {top:<21} {item.path}")
    lines.append("")
    lines.append("Worst rules across corpus:")
    for rule in report.worst_rules:
        lines.append(
            f"  {rule.rule_id:<21} loss={rule.weighted_loss:.2f} "
            f"affected={rule.affected_count} fail={rule.fail_count}"
        )
    return "\n".join(lines)


def render_batch_json(report: BatchReport) -> str:
    payload = {
        "average_score": report.average_score,
        "average_grade": report.average_grade,
        "count_by_grade": report.count_by_grade,
        "files": [
            {
                "path": item.path,
                "score": item.score,
                "grade": item.grade,
                "top_failing_rule": None
                if item.top_failing_rule is None
                else {
                    "rule_id": item.top_failing_rule.rule_id,
                    "title": item.top_failing_rule.title,
                    "severity": item.top_failing_rule.severity.value,
                },
            }
            for item in report.files
        ],
        "worst_rules": [
            {
                "rule_id": rule.rule_id,
                "title": rule.title,
                "fail_count": rule.fail_count,
                "affected_count": rule.affected_count,
                "weighted_loss": round(rule.weighted_loss, 4),
            }
            for rule in report.worst_rules
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=True)


def render_batch_markdown(report: BatchReport) -> str:
    lines = [
        "# GEO/AEO batch scan",
        "",
        f"**Average score:** {report.average_score}/100 (grade {report.average_grade})",
        "",
        "| Grade | Count |",
        "| --- | --- |",
    ]
    for grade, count in report.count_by_grade.items():
        lines.append(f"| {grade} | {count} |")
    lines.extend(
        [
            "",
            "## Leaderboard",
            "",
            "| Score | Grade | Top issue | Path |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in report.files:
        top = item.top_failing_rule.rule_id if item.top_failing_rule else "none"
        lines.append(f"| {item.score} | {item.grade} | {top} | {item.path} |")
    lines.extend(
        [
            "",
            "## Worst rules across corpus",
            "",
            "| Rule | Weighted loss | Affected | Failures |",
            "| --- | --- | --- | --- |",
        ]
    )
    for rule in report.worst_rules:
        lines.append(
            f"| {rule.rule_id} | {rule.weighted_loss:.2f} | "
            f"{rule.affected_count} | {rule.fail_count} |"
        )
    return "\n".join(lines)


def render_batch_html(report: BatchReport) -> str:
    file_rows = []
    for item in report.files:
        top = item.top_failing_rule.rule_id if item.top_failing_rule else "none"
        file_rows.append(
            "<tr>"
            f"<td>{item.score}/100</td>"
            f'<td><span class="grade-small grade-{_escape(item.grade.lower())}">'
            f"{_escape(item.grade)}</span></td>"
            f"<td>{_escape(top)}</td>"
            f"<td>{_escape(item.path)}</td>"
            "</tr>"
        )
    rule_rows = []
    for rule in report.worst_rules:
        rule_rows.append(
            "<tr>"
            f"<td>{_escape(rule.title)}<br><small>{_escape(rule.rule_id)}</small></td>"
            f"<td>{rule.weighted_loss:.2f}</td>"
            f"<td>{rule.affected_count}</td>"
            f"<td>{rule.fail_count}</td>"
            "</tr>"
        )
    grade_counts = "".join(
        f"<li><strong>{_escape(grade)}</strong> {count}</li>"
        for grade, count in report.count_by_grade.items()
    )
    return _html_page(
        "GEO/AEO batch scan",
        f"""
<section class="summary">
  <div>
    <p class="label">Corpus average</p>
    <p class="score">{report.average_score}<span>/100</span></p>
  </div>
  <div class="grade grade-{_escape(report.average_grade.lower())}">
    {_escape(report.average_grade)}
  </div>
</section>
<section>
  <h2>Grade counts</h2>
  <ul class="grade-counts">{grade_counts}</ul>
</section>
<section>
  <h2>Leaderboard</h2>
  <table>
    <thead><tr><th>Score</th><th>Grade</th><th>Top issue</th><th>Path</th></tr></thead>
    <tbody>{"".join(file_rows)}</tbody>
  </table>
</section>
<section>
  <h2>Worst rules across corpus</h2>
  <table>
    <thead>
      <tr><th>Rule</th><th>Weighted loss</th><th>Affected</th><th>Failures</th></tr>
    </thead>
    <tbody>{"".join(rule_rows)}</tbody>
  </table>
</section>
""",
    )


def _html_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{_escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #172026;
      --muted: #59656f;
      --line: #d9dee3;
      --page: #f7f8fa;
      --panel: #ffffff;
      --good: #237a4b;
      --warn: #986600;
      --bad: #b3261e;
      --accent: #255f85;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--page);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.45;
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 24px 48px;
    }}
    h1 {{ margin: 0 0 20px; font-size: 32px; letter-spacing: 0; }}
    h2 {{ margin: 28px 0 12px; font-size: 20px; letter-spacing: 0; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}
    th {{ color: var(--muted); font-weight: 700; }}
    small {{ color: var(--muted); }}
    .summary {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 20px;
      background: var(--panel);
      border: 1px solid var(--line);
    }}
    .label {{ margin: 0; color: var(--muted); font-size: 13px; text-transform: uppercase; }}
    .score {{ margin: 4px 0 0; font-size: 48px; font-weight: 700; }}
    .score span {{ color: var(--muted); font-size: 22px; font-weight: 400; }}
    .grade, .grade-small {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 6px;
      color: #ffffff;
      font-weight: 700;
    }}
    .grade {{ width: 86px; height: 86px; font-size: 42px; }}
    .grade-small {{ min-width: 30px; height: 24px; padding: 0 8px; }}
    .grade-a, .grade-b {{ background: var(--good); }}
    .grade-c, .grade-d {{ background: var(--warn); }}
    .grade-f {{ background: var(--bad); }}
    .status {{ font-weight: 700; }}
    .status-pass {{ color: var(--good); }}
    .status-warn {{ color: var(--warn); }}
    .status-fail {{ color: var(--bad); }}
    .bar {{ height: 12px; width: 100%; background: #e8edf1; border-radius: 6px; overflow: hidden; }}
    .bar span {{ display: block; height: 100%; background: var(--accent); }}
    .category-table th {{ width: 180px; }}
    .category-table td:last-child {{ width: 88px; color: var(--muted); }}
    .grade-counts {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      padding: 0;
      margin: 0;
      list-style: none;
    }}
    .grade-counts li {{
      padding: 8px 12px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
    }}
    @media print {{
      body {{ background: #ffffff; }}
      main {{ max-width: none; padding: 16px; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>{_escape(title)}</h1>
    {body}
  </main>
</body>
</html>"""
