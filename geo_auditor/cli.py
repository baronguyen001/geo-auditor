"""Command-line interface for geo-auditor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from geo_auditor import __version__
from geo_auditor.batch import scan_paths
from geo_auditor.config import apply_config, load_config
from geo_auditor.diff import (
    diff_report_files,
    render_diff_json,
    render_diff_markdown,
    render_diff_text,
)
from geo_auditor.fetch import fetch_url, is_url
from geo_auditor.llms_txt import generate_llms_txt
from geo_auditor.parse import parse_content
from geo_auditor.remediate import (
    build_remediation,
    render_remediation_json,
    render_remediation_markdown,
    render_remediation_text,
)
from geo_auditor.report import (
    render_batch_html,
    render_batch_json,
    render_batch_markdown,
    render_batch_text,
    render_diff_html,
    render_html,
    render_json,
    render_markdown,
    render_remediation_html,
    render_text,
)
from geo_auditor.rules import ALL_RULES
from geo_auditor.rules.base import Rule
from geo_auditor.score import build_report


def _configure_streams() -> None:
    # Force UTF-8 so the (ASCII) output never trips a Windows cp1252 console.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def _load(target: str, *, offline: bool, timeout: float) -> str:
    if is_url(target):
        if offline:
            raise ValueError("Refusing to fetch a URL in --offline mode.")
        return fetch_url(target, timeout=timeout)
    path = Path(target)
    if not path.is_file():
        raise FileNotFoundError(f"No such file: {target}")
    return path.read_text(encoding="utf-8", errors="replace")


def _rules_from_args(args: argparse.Namespace) -> tuple[Rule, ...]:
    config = load_config(args.config)
    return apply_config(ALL_RULES, config)


def _min_score_from_args(args: argparse.Namespace) -> int | None:
    if args.min_score is not None:
        return args.min_score
    config = load_config(args.config)
    return config.defaults.min_score


def _cmd_check(args: argparse.Namespace) -> int:
    try:
        text = _load(args.target, offline=args.offline, timeout=args.timeout)
        rules = _rules_from_args(args)
        min_score = _min_score_from_args(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    doc = parse_content(text, fmt=args.format_in)
    report = build_report(doc, rules=rules)
    renderers = {
        "text": render_text,
        "json": render_json,
        "md": render_markdown,
        "html": render_html,
    }
    print(renderers[args.format](report))
    if min_score is not None and report.score < min_score:
        print(
            f"\nFAILED: score {report.score} is below --min-score {min_score}.",
            file=sys.stderr,
        )
        return 1
    return 0


def _cmd_scan(args: argparse.Namespace) -> int:
    try:
        rules = _rules_from_args(args)
        min_score = _min_score_from_args(args)
        report = scan_paths(args.paths, rules=rules)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    renderers = {
        "text": render_batch_text,
        "json": render_batch_json,
        "md": render_batch_markdown,
        "html": render_batch_html,
    }
    print(renderers[args.format](report))
    if min_score is not None and report.average_score < min_score:
        print(
            "\nFAILED: corpus average score "
            f"{report.average_score} is below --min-score {min_score}.",
            file=sys.stderr,
        )
        return 1
    return 0


def _cmd_fix(args: argparse.Namespace) -> int:
    try:
        text = _load(args.target, offline=args.offline, timeout=args.timeout)
        rules = _rules_from_args(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    doc = parse_content(text, fmt=args.format_in)
    report = build_report(doc, rules=rules)
    plan = build_remediation(report, top=args.top)
    renderers = {
        "text": render_remediation_text,
        "json": render_remediation_json,
        "md": render_remediation_markdown,
        "html": render_remediation_html,
    }
    print(renderers[args.format](plan))
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    try:
        diff = diff_report_files(Path(args.before_json), Path(args.after_json))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    renderers = {
        "text": render_diff_text,
        "json": render_diff_json,
        "md": render_diff_markdown,
        "html": render_diff_html,
    }
    print(renderers[args.format](diff))
    return 0


def _cmd_rules(args: argparse.Namespace) -> int:
    try:
        rules = _rules_from_args(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("geo-auditor rules:")
    for rule in rules:
        print(f"  {rule.id:<20} [{rule.category.value:<16}] w={rule.weight:<4} {rule.title}")
    return 0


def _cmd_init_llms(args: argparse.Namespace) -> int:
    try:
        text = _load(args.target, offline=args.offline, timeout=args.timeout)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    doc = parse_content(text, fmt=args.format_in)
    print(generate_llms_txt(doc, site_name=args.site_name), end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="geo-audit",
        description="Score how likely AI answer engines are to cite your content.",
    )
    parser.add_argument("--version", action="version", version=f"geo-auditor {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    config_common = argparse.ArgumentParser(add_help=False)
    config_common.add_argument(
        "--config",
        default=None,
        help="Path to a .geo-audit.toml config file (default: auto-discover in CWD).",
    )

    common = argparse.ArgumentParser(add_help=False, parents=[config_common])
    common.add_argument("target", help="Path to an HTML/Markdown file, or a URL.")
    common.add_argument(
        "--format-in",
        choices=("auto", "html", "markdown"),
        default="auto",
        help="Input format (default: auto-detect).",
    )
    common.add_argument(
        "--offline",
        action="store_true",
        help="Never make network requests (URLs are rejected).",
    )
    common.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="URL fetch timeout in seconds (default: 15).",
    )

    check = sub.add_parser("check", parents=[common], help="Audit a page.")
    check.add_argument(
        "--format",
        choices=("text", "json", "md", "html"),
        default="text",
        help="Output format (default: text).",
    )
    check.add_argument(
        "--min-score",
        type=int,
        default=None,
        help="Exit non-zero if the score is below this threshold (for CI gates).",
    )
    check.set_defaults(func=_cmd_check)

    fix = sub.add_parser("fix", parents=[common], help="Build a prioritized remediation plan.")
    fix.add_argument(
        "--format",
        choices=("text", "md", "json", "html"),
        default="text",
        help="Output format (default: text).",
    )
    fix.add_argument(
        "--top",
        type=int,
        default=None,
        help="Limit output to the N highest-impact items (default: all).",
    )
    fix.set_defaults(func=_cmd_fix)

    scan = sub.add_parser(
        "scan",
        parents=[config_common],
        help="Audit a local content corpus.",
    )
    scan.add_argument("paths", nargs="+", help="Local files or directories to scan.")
    scan.add_argument(
        "--format",
        choices=("text", "json", "md", "html"),
        default="text",
        help="Output format (default: text).",
    )
    scan.add_argument(
        "--min-score",
        type=int,
        default=None,
        help=("Exit non-zero if the corpus average score is below this threshold (for CI gates)."),
    )
    scan.set_defaults(func=_cmd_scan)

    diff = sub.add_parser("diff", help="Compare two JSON audit reports.")
    diff.add_argument("before_json", help="Earlier geo-audit check --format json output.")
    diff.add_argument("after_json", help="Later geo-audit check --format json output.")
    diff.add_argument(
        "--format",
        choices=("text", "json", "md", "html"),
        default="text",
        help="Output format (default: text).",
    )
    diff.set_defaults(func=_cmd_diff)

    rules = sub.add_parser("rules", parents=[config_common], help="List all rules.")
    rules.set_defaults(func=_cmd_rules)

    init = sub.add_parser("init-llms", parents=[common], help="Generate a llms.txt draft.")
    init.add_argument("--site-name", default=None, help="Override the site name.")
    init.set_defaults(func=_cmd_init_llms)

    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_streams()
    parser = build_parser()
    args = parser.parse_args(argv)
    func = args.func
    exit_code: int = func(args)
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
