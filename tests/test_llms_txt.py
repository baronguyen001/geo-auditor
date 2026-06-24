"""Tests for llms.txt generation."""

from __future__ import annotations

from geo_auditor.llms_txt import generate_llms_txt
from geo_auditor.models import Document, Heading


def test_generate_from_strong_doc(strong_doc: Document) -> None:
    out = generate_llms_txt(strong_doc)
    assert out.startswith("# How to Brew")
    assert "## Key sections" in out
    assert "## Notes for AI assistants" in out
    assert out.endswith("\n")


def test_site_name_override() -> None:
    doc = Document(h1="Original", headings=[Heading(2, "Section A")])
    out = generate_llms_txt(doc, site_name="My Brand")
    assert out.startswith("# My Brand")
    assert "- Section A" in out


def test_empty_document() -> None:
    out = generate_llms_txt(Document())
    assert "# Your Site" in out
    assert "## Key sections" not in out


def test_long_summary_is_truncated() -> None:
    long_text = "word " * 200
    doc = Document(meta={"description": long_text})
    out = generate_llms_txt(doc, site_name="Brand")
    summary_line = next(line for line in out.splitlines() if line.startswith("> "))
    assert summary_line.endswith("...")
    assert len(summary_line) <= 284
