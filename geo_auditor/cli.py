"""Command-line interface for geo-auditor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from geo_auditor import __version__
from geo_auditor.fetch import fetch_url, is_url
from geo_auditor.llms_txt import generate_llms_txt
from geo_auditor.parse import parse_content
from geo_auditor.report import render_json, render_markdown, render_text
from geo_auditor.rules import ALL_RULES
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


def _cmd_check(args: argparse.Namespace) -> int:
    try:
        text = _load(args.target, offline=args.offline, timeout=args.timeout)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    doc = parse_content(text, fmt=args.format_in)
    report = build_report(doc)
    renderers = {
        "text": render_text,
        "json": render_json,
        "md": render_markdown,
    }
    print(renderers[args.format](report))
    if args.min_score is not None and report.score < args.min_score:
        print(
            f"\nFAILED: score {report.score} is below --min-score {args.min_score}.",
            file=sys.stderr,
        )
        return 1
    return 0


def _cmd_rules(_: argparse.Namespace) -> int:
    print("geo-auditor rules:")
    for rule in ALL_RULES:
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

    common = argparse.ArgumentParser(add_help=False)
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
        choices=("text", "json", "md"),
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

    rules = sub.add_parser("rules", help="List all rules.")
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
