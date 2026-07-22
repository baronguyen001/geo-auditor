"""Readability rules for clear, citeable answer text."""

from __future__ import annotations

import re

from geo_auditor.models import Category, Document, RuleResult
from geo_auditor.rules.base import BaseRule, result

_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")
_GENERIC_ANCHORS = {
    "",
    "click here",
    "read more",
    "here",
    "link",
    "this",
    "learn more",
    "more",
    "read on",
}


def _word_count(text: str) -> int:
    return len(text.split())


class SentenceLengthRule(BaseRule):
    id = "sentence-length"
    title = "Concise sentence length"
    category = Category.READABILITY
    weight = 1.0

    def check(self, doc: Document) -> RuleResult:
        sentences = [
            sentence.strip() for sentence in _SENTENCE_SPLIT_RE.split(doc.text) if sentence.strip()
        ]
        if not sentences:
            return result(
                self,
                0.0,
                "No sentence text found to evaluate.",
                "Add clear body copy with concise sentences that answer one idea at a time.",
            )
        avg = sum(_word_count(sentence) for sentence in sentences) / len(sentences)
        score = 1.0 if avg <= 20 else 1.0 - ((avg - 20) / 20)
        fix = "" if score >= 0.999 else "Split long sentences so the average stays near 20 words."
        return result(
            self,
            score,
            f"Average sentence length is {avg:.0f} words across {len(sentences)} sentence(s).",
            fix,
        )


class ParagraphLengthRule(BaseRule):
    id = "paragraph-length"
    title = "Concise paragraph length"
    category = Category.READABILITY
    weight = 1.0

    def check(self, doc: Document) -> RuleResult:
        paragraphs = [paragraph for paragraph in doc.paragraphs if paragraph.strip()]
        if not paragraphs:
            return result(
                self,
                0.0,
                "No paragraphs found to evaluate.",
                "Break the page into short, self-contained paragraphs.",
            )
        avg = sum(_word_count(paragraph) for paragraph in paragraphs) / len(paragraphs)
        score = 1.0 if avg <= 80 else 1.0 - ((avg - 80) / 80)
        fix = "" if score >= 0.999 else "Break wall-of-text paragraphs into shorter chunks."
        return result(
            self,
            score,
            f"Average paragraph length is {avg:.0f} words across {len(paragraphs)} paragraph(s).",
            fix,
        )


class DescriptiveAnchorRule(BaseRule):
    id = "descriptive-anchor"
    title = "Descriptive link anchors"
    category = Category.READABILITY
    weight = 1.0

    def check(self, doc: Document) -> RuleResult:
        if not doc.links:
            return result(self, 1.0, "No links to evaluate.", "")
        descriptive = sum(
            1 for link in doc.links if link.text.strip().lower() not in _GENERIC_ANCHORS
        )
        ratio = descriptive / len(doc.links)
        detail = f"{descriptive}/{len(doc.links)} link anchor(s) are descriptive."
        fix = "" if ratio >= 0.999 else "Replace generic anchors with specific destination text."
        return result(self, ratio, detail, fix)
