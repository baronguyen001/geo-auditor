"""Machine-readable rules: structured data engines can parse directly."""

from __future__ import annotations

import re

from geo_auditor.models import Category, Document, RuleResult
from geo_auditor.rules.base import BaseRule, result

_RELEVANT_TYPES = {
    "article",
    "blogposting",
    "newsarticle",
    "webpage",
    "faqpage",
    "howto",
    "product",
    "qapage",
    "techarticle",
}

_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "to",
    "in",
    "for",
    "on",
    "with",
    "your",
    "you",
    "is",
    "are",
    "how",
    "what",
    "why",
}
_WORD_RE = re.compile(r"[a-z0-9]+")


def _types(block: dict[str, object]) -> set[str]:
    raw = block.get("@type", "")
    values = raw if isinstance(raw, list) else [raw]
    return {v.lower() for v in values if isinstance(v, str)}


class JsonLdRule(BaseRule):
    id = "json-ld-schema"
    title = "Schema.org structured data"
    category = Category.MACHINE_READABLE
    weight = 3.0

    def check(self, doc: Document) -> RuleResult:
        if not doc.json_ld:
            return result(
                self,
                0.0,
                "No JSON-LD structured data found.",
                "Add a schema.org JSON-LD block (Article, FAQPage or HowTo) so "
                "engines can read the page as data.",
            )
        all_types: set[str] = set()
        for block in doc.json_ld:
            all_types |= _types(block)
        relevant = all_types & _RELEVANT_TYPES
        if relevant:
            return result(
                self,
                1.0,
                f"JSON-LD present with types: {', '.join(sorted(relevant))}.",
                "",
            )
        return result(
            self,
            0.5,
            "JSON-LD present but no content type (Article/FAQPage/HowTo).",
            "Mark the main content with a relevant schema.org @type.",
        )


class FaqRule(BaseRule):
    id = "faq"
    title = "FAQ / Q&A blocks"
    category = Category.MACHINE_READABLE
    weight = 2.0

    def check(self, doc: Document) -> RuleResult:
        has_schema = any(_types(b) & {"faqpage", "qapage"} for b in doc.json_ld)
        if has_schema:
            return result(
                self,
                1.0,
                "FAQPage / QAPage schema is present.",
                "",
            )
        if doc.has_faq:
            return result(
                self,
                0.6,
                "An FAQ section exists but lacks FAQPage schema.",
                "Wrap the FAQ in FAQPage JSON-LD so engines extract each Q&A.",
            )
        return result(
            self,
            0.0,
            "No FAQ section or FAQPage schema.",
            "Add a short FAQ answering common follow-up questions, with FAQPage schema.",
        )


class MetaTagsRule(BaseRule):
    id = "meta-tags"
    title = "Title and meta description"
    category = Category.MACHINE_READABLE
    weight = 1.0

    def check(self, doc: Document) -> RuleResult:
        title_len = len(doc.title)
        desc = doc.meta.get("description", "")
        desc_len = len(desc)
        title_ok = 15 <= title_len <= 70
        desc_ok = 50 <= desc_len <= 170
        score = 0.5 * (1.0 if title_ok else 0.0) + 0.5 * (1.0 if desc_ok else 0.0)
        problems = []
        if not title_ok:
            problems.append(f"title {title_len} chars (want 15-70)")
        if not desc_ok:
            problems.append(f"meta description {desc_len} chars (want 50-170)")
        detail = "Title and description are well sized." if not problems else "; ".join(problems)
        fix = (
            "" if score >= 0.999 else "Set a 15-70 char <title> and a 50-170 char meta description."
        )
        return result(self, score, detail, fix)


class EntityClarityRule(BaseRule):
    id = "entity-clarity"
    title = "Title / H1 alignment"
    category = Category.MACHINE_READABLE
    weight = 1.0

    def check(self, doc: Document) -> RuleResult:
        if not doc.title or not doc.h1:
            missing = "title" if not doc.title else "H1"
            return result(
                self,
                0.0,
                f"Missing {missing}; the page topic is ambiguous to engines.",
                "Provide both a <title> and a single clear H1 naming the topic.",
            )
        title_words = set(_WORD_RE.findall(doc.title.lower())) - _STOPWORDS
        h1_words = set(_WORD_RE.findall(doc.h1.lower())) - _STOPWORDS
        if not title_words or not h1_words:
            return result(
                self,
                0.5,
                "Title or H1 carries no distinctive keywords.",
                "Name the core entity/topic in both the title and H1.",
            )
        overlap = len(title_words & h1_words) / len(title_words | h1_words)
        score = min(1.0, overlap / 0.3)
        detail = f"Title/H1 keyword overlap is {overlap:.0%}."
        fix = "" if score >= 0.999 else "Align the title and H1 around the same core entity."
        return result(self, score, detail, fix)
