"""Shared fixtures for the test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from geo_auditor.models import Document
from geo_auditor.parse import parse_content

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def strong_html() -> str:
    return (FIXTURES / "strong_page.html").read_text(encoding="utf-8")


@pytest.fixture
def weak_md() -> str:
    return (FIXTURES / "weak_page.md").read_text(encoding="utf-8")


@pytest.fixture
def strong_doc(strong_html: str) -> Document:
    return parse_content(strong_html, fmt="html")


@pytest.fixture
def weak_doc(weak_md: str) -> Document:
    return parse_content(weak_md, fmt="markdown")
