"""Tests for the optional URL fetcher (no real network access)."""

from __future__ import annotations

from typing import Any

import pytest

from geo_auditor import fetch


def test_is_url() -> None:
    assert fetch.is_url("https://example.com")
    assert fetch.is_url("http://example.com")
    assert not fetch.is_url("./local.html")
    assert not fetch.is_url("ftp://example.com")


def test_fetch_url_rejects_non_url() -> None:
    with pytest.raises(ValueError, match="Not an HTTP"):
        fetch.fetch_url("local.html")


class _FakeHeaders:
    def get_content_charset(self) -> str:
        return "utf-8"


class _FakeResponse:
    headers = _FakeHeaders()

    def read(self) -> bytes:
        return b"<html><body><p>hello</p></body></html>"

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_fetch_url_decodes_body(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request: Any, timeout: float = 0.0) -> _FakeResponse:
        return _FakeResponse()

    monkeypatch.setattr(fetch.urllib.request, "urlopen", fake_urlopen)
    body = fetch.fetch_url("https://example.com")
    assert "hello" in body
