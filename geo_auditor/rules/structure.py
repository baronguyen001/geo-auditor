"""Structure rules: can an answer engine lift a clean answer from the page?"""

from __future__ import annotations

import re

from geo_auditor.models import Category, Document, RuleResult
from geo_auditor.rules.base import BaseRule, result

_QUESTION_STARTERS = (
    "who",
    "what",
    "why",
    "how",
    "when",
    "where",
    "which",
    "can",
    "does",
    "do",
    "is",
    "are",
    "should",
    "will",
)


def _is_question(text: str) -> bool:
    stripped = text.strip().lower()
    if stripped.endswith("?"):
        return True
    first = re.split(r"\s+", stripped, maxsplit=1)[0] if stripped else ""
    return first in _QUESTION_STARTERS


class AnswerFirstRule(BaseRule):
    id = "answer-first"
    title = "Answer up front"
    category = Category.STRUCTURE
    weight = 3.0

    def check(self, doc: Document) -> RuleResult:
        if not doc.paragraphs:
            return result(
                self,
                0.0,
                "No paragraph text found before the body.",
                "Open with a 20-80 word paragraph that directly answers the page's "
                "core question, before any heading.",
            )
        words = len(doc.paragraphs[0].split())
        if 20 <= words <= 80:
            return result(
                self,
                1.0,
                f"Lead paragraph is {words} words - a liftable direct answer.",
                "",
            )
        if words < 20:
            return result(
                self,
                0.4,
                f"Lead paragraph is only {words} words; too thin to be quoted.",
                "Expand the opening to a self-contained 20-80 word answer.",
            )
        return result(
            self,
            0.5,
            f"Lead paragraph is {words} words; engines prefer a tighter answer.",
            "Front-load a concise 20-80 word answer, then expand below it.",
        )


class QuestionHeadingsRule(BaseRule):
    id = "question-headings"
    title = "Question-shaped headings"
    category = Category.STRUCTURE
    weight = 2.0

    def check(self, doc: Document) -> RuleResult:
        subs = [h for h in doc.headings if h.level in (2, 3)]
        if not subs:
            return result(
                self,
                0.0,
                "No H2/H3 subheadings to match conversational queries.",
                "Add H2/H3 subheadings, several phrased as natural questions "
                "users ask (e.g. 'How does X work?').",
            )
        questions = sum(1 for h in subs if _is_question(h.text))
        ratio = questions / len(subs)
        score = min(1.0, ratio / 0.3)
        detail = f"{questions}/{len(subs)} subheadings are question-shaped."
        fix = (
            ""
            if score >= 0.999
            else "Rephrase more subheadings as the questions readers actually ask."
        )
        return result(self, score, detail, fix)


class ScannableRule(BaseRule):
    id = "scannable"
    title = "Scannable formatting"
    category = Category.STRUCTURE
    weight = 2.0

    def check(self, doc: Document) -> RuleResult:
        if not doc.paragraphs:
            return result(
                self,
                0.0,
                "No body paragraphs to assess.",
                "Break content into short paragraphs and bulleted lists.",
            )
        avg = sum(len(p.split()) for p in doc.paragraphs) / len(doc.paragraphs)
        short_para = 1.0 if avg <= 90 else max(0.0, 1.0 - (avg - 90) / 90)
        has_lists = 1.0 if doc.lists >= 1 else 0.0
        score = round(0.6 * short_para + 0.4 * has_lists, 4)
        detail = f"Avg paragraph {avg:.0f} words; {doc.lists} list(s)."
        fixes = []
        if short_para < 0.999:
            fixes.append("shorten paragraphs to under ~90 words")
        if not has_lists:
            fixes.append("add bullet or numbered lists")
        return result(self, score, detail, ("; ".join(fixes)).capitalize())


class HeadingHierarchyRule(BaseRule):
    id = "heading-hierarchy"
    title = "Clean heading hierarchy"
    category = Category.STRUCTURE
    weight = 1.0

    def check(self, doc: Document) -> RuleResult:
        if not doc.headings:
            return result(
                self,
                0.0,
                "Document has no headings.",
                "Add a single H1 and nested H2/H3 sections.",
            )
        h1_count = sum(1 for h in doc.headings if h.level == 1)
        skipped = False
        prev = doc.headings[0].level
        for heading in doc.headings[1:]:
            if heading.level > prev + 1:
                skipped = True
                break
            prev = heading.level
        score = 1.0
        problems = []
        if h1_count != 1:
            score -= 0.5
            problems.append(f"{h1_count} H1 tags (want exactly 1)")
        if skipped:
            score -= 0.5
            problems.append("a heading level is skipped")
        detail = "Hierarchy is clean." if not problems else "; ".join(problems)
        fix = "" if score >= 0.999 else "Use exactly one H1 and never skip heading levels."
        return result(self, score, detail, fix)


class ContentDepthRule(BaseRule):
    id = "content-depth"
    title = "Sufficient content depth"
    category = Category.STRUCTURE
    weight = 1.0

    def check(self, doc: Document) -> RuleResult:
        words = doc.word_count
        if words >= 300:
            return result(
                self,
                1.0,
                f"{words} words - enough substance to be quotable.",
                "",
            )
        if words >= 150:
            return result(
                self,
                0.5,
                f"Only {words} words; thin pages are rarely cited.",
                "Expand to 300+ words of substantive, on-topic content.",
            )
        return result(
            self,
            0.0,
            f"Only {words} words; far too thin to be cited.",
            "Add substantive content (aim for 300+ words on the topic).",
        )


class TldrSummaryRule(BaseRule):
    id = "tldr-summary"
    title = "Extractable summary"
    category = Category.STRUCTURE
    weight = 1.0

    def check(self, doc: Document) -> RuleResult:
        if doc.has_summary:
            return result(
                self,
                1.0,
                "A TL;DR / key-takeaways block is present.",
                "",
            )
        return result(
            self,
            0.0,
            "No TL;DR or key-takeaways section detected.",
            "Add a short 'Key takeaways' or 'TL;DR' block that engines can quote.",
        )
