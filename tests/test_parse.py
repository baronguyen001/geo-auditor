"""Tests for the HTML/Markdown parser."""

from __future__ import annotations

from geo_auditor.models import Document
from geo_auditor.parse import detect_format, parse_content


def test_detect_format_html() -> None:
    assert detect_format("<!DOCTYPE html><html><body><p>hi</p></body></html>") == "html"
    assert detect_format("<div>hello</div>") == "html"


def test_detect_format_markdown() -> None:
    assert detect_format("# Title\n\nSome prose.") == "markdown"
    assert detect_format("Just a sentence with no tags.") == "markdown"


def test_parse_strong_html(strong_doc: Document) -> None:
    assert strong_doc.title.startswith("How to Brew")
    assert strong_doc.h1.startswith("How to Brew")
    assert any(h.level == 1 for h in strong_doc.headings)
    assert len([h for h in strong_doc.headings if h.level == 2]) >= 3
    assert strong_doc.lists >= 1
    assert strong_doc.meta["author"] == "Jordan Rivera"
    assert "description" in strong_doc.meta
    assert strong_doc.word_count > 300


def test_parse_json_ld(strong_doc: Document) -> None:
    types = {
        t.lower()
        for block in strong_doc.json_ld
        for t in [block.get("@type", "")]
        if isinstance(t, str)
    }
    assert "article" in types
    assert "faqpage" in types
    assert strong_doc.has_faq is True


def test_parse_dates_and_summary(strong_doc: Document) -> None:
    assert any("2026" in d for d in strong_doc.dates)
    assert strong_doc.has_summary is True


def test_external_vs_internal_links() -> None:
    html = (
        '<html><body><p><a href="https://example.com">ext</a>'
        '<a href="/local">internal</a><a href="">empty</a></p></body></html>'
    )
    doc = parse_content(html, fmt="html")
    assert len(doc.links) == 2
    assert len(doc.external_links) == 1


def test_markdown_tables_and_lists() -> None:
    md_text = (
        "# Guide\n\n"
        "Intro paragraph.\n\n"
        "## How does it work?\n\n"
        "- one\n- two\n\n"
        "| a | b |\n| --- | --- |\n| 1 | 2 |\n"
    )
    doc = parse_content(md_text, fmt="markdown")
    assert doc.lists >= 1
    assert doc.tables >= 1
    assert any(h.text.endswith("?") for h in doc.headings)


def test_malformed_json_ld_is_ignored() -> None:
    html = (
        '<html><head><script type="application/ld+json">{not valid json}'
        "</script></head><body><p>hi</p></body></html>"
    )
    doc = parse_content(html, fmt="html")
    assert doc.json_ld == []


def test_json_ld_list_payload() -> None:
    html = (
        '<html><head><script type="application/ld+json">'
        '[{"@type": "Article"}, "skip-me", {"@type": "Person"}]'
        "</script></head><body><p>hi</p></body></html>"
    )
    doc = parse_content(html, fmt="html")
    assert len(doc.json_ld) == 2


def test_auto_format_roundtrip(weak_md: str) -> None:
    doc = parse_content(weak_md, fmt="auto")
    assert doc.h1 == "cheap widgets"
    assert doc.title == "cheap widgets"  # falls back to h1


def test_title_falls_back_to_h1() -> None:
    doc = parse_content("<html><body><h1>Only H1</h1><p>x</p></body></html>", fmt="html")
    assert doc.title == "Only H1"
