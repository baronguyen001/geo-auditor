"""Parse HTML or Markdown into the normalized :class:`Document` model.

Markdown is rendered to HTML first so there is a single extraction path. All
extraction is local and deterministic; no network access happens here.
"""

from __future__ import annotations

import json
import re
from typing import Literal

import markdown as md
from bs4 import BeautifulSoup, Tag

from geo_auditor.models import Document, Heading, Link

Format = Literal["html", "markdown", "auto"]

_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_DATE_WORD_RE = re.compile(
    r"\b(updated|last updated|published|posted|revised|reviewed)\b", re.IGNORECASE
)
_FAQ_RE = re.compile(r"\b(faq|frequently asked questions?)\b", re.IGNORECASE)
_SUMMARY_RE = re.compile(
    r"\b(tl;?dr|tldr|in short|key takeaways?|summary|in a nutshell|bottom line)\b",
    re.IGNORECASE,
)


def detect_format(text: str) -> Literal["html", "markdown"]:
    """Best-effort sniff of whether *text* is HTML or Markdown."""
    head = text.lstrip()[:512].lower()
    html_markers = ("<!doctype", "<html", "<head", "<body", "<div", "<p>", "<p ", "<h1")
    if head.startswith("<") and any(marker in head for marker in html_markers):
        return "html"
    if re.search(r"<[a-z][a-z0-9]*[ >/]", head) and "<" in head[:5]:
        return "html"
    return "markdown"


def parse_content(text: str, *, fmt: Format = "auto") -> Document:
    """Parse *text* into a :class:`Document`.

    ``fmt="auto"`` sniffs the format. Markdown is converted to HTML using the
    ``tables`` and ``fenced_code`` extensions before extraction.
    """
    resolved: Literal["html", "markdown"]
    resolved = detect_format(text) if fmt == "auto" else fmt
    html = (
        md.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
        if resolved == "markdown"
        else text
    )
    soup = BeautifulSoup(html, "html.parser")
    return _extract(soup)


def _tag_text(tag: Tag) -> str:
    return " ".join(str(tag.get_text(" ", strip=True)).split())


def _extract(soup: BeautifulSoup) -> Document:
    doc = Document()

    title_tag = soup.find("title")
    if isinstance(title_tag, Tag):
        doc.title = _tag_text(title_tag)

    for level in range(1, 7):
        for tag in soup.find_all(f"h{level}"):
            if isinstance(tag, Tag):
                text = _tag_text(tag)
                if text:
                    doc.headings.append(Heading(level=level, text=text))

    h1s = [h.text for h in doc.headings if h.level == 1]
    if h1s:
        doc.h1 = h1s[0]
    if not doc.title and doc.h1:
        doc.title = doc.h1

    for tag in soup.find_all("p"):
        if isinstance(tag, Tag):
            text = _tag_text(tag)
            if text:
                doc.paragraphs.append(text)

    for tag in soup.find_all("a"):
        if not isinstance(tag, Tag):
            continue
        href = str(tag.get("href", "")).strip()
        if not href:
            continue
        external = href.startswith(("http://", "https://"))
        doc.links.append(Link(href=href, text=_tag_text(tag), external=external))

    doc.tables = len(soup.find_all("table"))
    doc.lists = len(soup.find_all(["ul", "ol"]))

    doc.json_ld = _extract_json_ld(soup)
    doc.meta = _extract_meta(soup)

    doc.text = " ".join(str(soup.get_text(" ", strip=True)).split())

    heading_text = " ".join(h.text for h in doc.headings)
    doc.has_faq = bool(_FAQ_RE.search(heading_text)) or _has_faq_schema(doc.json_ld)
    doc.has_summary = bool(_SUMMARY_RE.search(heading_text)) or _starts_with_summary(doc)
    doc.dates = _extract_dates(doc)
    return doc


def _extract_json_ld(soup: BeautifulSoup) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if not isinstance(tag, Tag):
            continue
        raw = tag.string or _tag_text(tag)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        if isinstance(data, dict):
            blocks.append(data)
        elif isinstance(data, list):
            blocks.extend(item for item in data if isinstance(item, dict))
    return blocks


def _extract_meta(soup: BeautifulSoup) -> dict[str, str]:
    meta: dict[str, str] = {}
    for tag in soup.find_all("meta"):
        if not isinstance(tag, Tag):
            continue
        key = tag.get("name") or tag.get("property")
        content = tag.get("content")
        if isinstance(key, str) and isinstance(content, str):
            meta[key.lower()] = content
    return meta


def _has_faq_schema(json_ld: list[dict[str, object]]) -> bool:
    return any(_type_matches(block, {"faqpage"}) for block in json_ld)


def _type_matches(block: dict[str, object], wanted: set[str]) -> bool:
    raw_type = block.get("@type", "")
    types = raw_type if isinstance(raw_type, list) else [raw_type]
    return any(isinstance(t, str) and t.lower() in wanted for t in types)


def _starts_with_summary(doc: Document) -> bool:
    if not doc.paragraphs:
        return False
    return bool(_SUMMARY_RE.search(doc.paragraphs[0]))


def _extract_dates(doc: Document) -> list[str]:
    found: list[str] = []
    for key in ("article:modified_time", "article:published_time", "date"):
        value = doc.meta.get(key)
        if value:
            found.append(value)
    for block in doc.json_ld:
        for key in ("dateModified", "datePublished"):
            raw = block.get(key)
            if isinstance(raw, str):
                found.append(raw)
    if _DATE_WORD_RE.search(doc.text):
        years = _YEAR_RE.findall(doc.text)
        found.extend(years[:3])
    return found
