"""Authority rules: does the page show its work? Engines favor citable facts."""

from __future__ import annotations

import re

from geo_auditor.models import Category, Document, RuleResult
from geo_auditor.rules.base import BaseRule, result

_STAT_RE = re.compile(
    r"\b\d[\d,]*(?:\.\d+)?\s?(?:%|percent|x|bn|billion|million|k\b|users?|"
    r"customers?|hours?|days?|years?|\$)",
    re.IGNORECASE,
)
# Currency symbols built via chr() so the source stays pure ASCII.
_CURRENCY_SYMBOLS = "$" + chr(0x20AC) + chr(0x00A3)  # $, euro, pound
_CURRENCY_RE = re.compile("[" + _CURRENCY_SYMBOLS + r"]\s?\d")
_AUTHOR_META = ("author", "article:author", "twitter:creator")
_BYLINE_RE = re.compile(r"\bby\s+[A-Z][a-z]+", re.MULTILINE)


class StatisticsRule(BaseRule):
    id = "statistics-cited"
    title = "Statistics with citations"
    category = Category.AUTHORITY
    weight = 3.0

    def check(self, doc: Document) -> RuleResult:
        stats = len(_STAT_RE.findall(doc.text)) + len(_CURRENCY_RE.findall(doc.text))
        citations = len(doc.external_links)
        if stats == 0:
            return result(
                self,
                0.0,
                "No statistics or quantified claims detected.",
                "Add concrete numbers (percentages, counts, dollars) - engines "
                "preferentially cite verifiable stats.",
            )
        if citations == 0:
            return result(
                self,
                0.5,
                f"{stats} stat(s) present but none are backed by an outbound source.",
                "Cite a source link next to each key statistic.",
            )
        return result(
            self,
            1.0,
            f"{stats} stat(s) supported by {citations} outbound citation(s).",
            "",
        )


class CitationsRule(BaseRule):
    id = "outbound-citations"
    title = "Outbound citations"
    category = Category.AUTHORITY
    weight = 2.0

    def check(self, doc: Document) -> RuleResult:
        count = len(doc.external_links)
        if count >= 2:
            return result(
                self,
                1.0,
                f"{count} outbound citation(s) to external sources.",
                "",
            )
        if count == 1:
            return result(
                self,
                0.5,
                "Only one outbound citation.",
                "Reference at least two reputable external sources.",
            )
        return result(
            self,
            0.0,
            "No outbound citations to authoritative sources.",
            "Link out to primary or authoritative sources to build trust.",
        )


class AuthorRule(BaseRule):
    id = "author-eeat"
    title = "Author / E-E-A-T signal"
    category = Category.AUTHORITY
    weight = 2.0

    def check(self, doc: Document) -> RuleResult:
        if any(doc.meta.get(key) for key in _AUTHOR_META):
            return result(self, 1.0, "Author metadata is present.", "")
        for block in doc.json_ld:
            if block.get("author"):
                return result(self, 1.0, "Author is declared in JSON-LD.", "")
        if _BYLINE_RE.search(doc.text):
            return result(
                self,
                0.6,
                "A visible byline exists but no author metadata.",
                "Add an author meta tag or schema.org author for stronger E-E-A-T.",
            )
        return result(
            self,
            0.0,
            "No author or byline signal.",
            "Attribute the content to a named author (byline + meta/schema).",
        )
