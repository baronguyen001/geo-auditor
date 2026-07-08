"""Multimedia and discoverability rules for richer answer citations."""

from __future__ import annotations

from geo_auditor.models import Category, Document, RuleResult
from geo_auditor.rules.base import BaseRule, result


class AltTextRule(BaseRule):
    id = "alt-text"
    title = "Descriptive image alt text"
    category = Category.MULTIMEDIA
    weight = 1.0

    def check(self, doc: Document) -> RuleResult:
        if not doc.images:
            return result(
                self,
                0.0,
                "No images found for visual context.",
                "Add relevant images with descriptive alt text where visuals support the answer.",
            )
        described = sum(1 for image in doc.images if image.alt.strip())
        ratio = described / len(doc.images)
        detail = f"{described}/{len(doc.images)} image(s) have non-empty alt text."
        fix = "" if ratio >= 0.999 else "Write specific alt text for every meaningful image."
        return result(self, ratio, detail, fix)


class TableDataRule(BaseRule):
    id = "table-data"
    title = "Parseable data tables"
    category = Category.MULTIMEDIA
    weight = 1.0

    def check(self, doc: Document) -> RuleResult:
        if doc.tables == 0:
            return result(
                self,
                0.0,
                "No tables found for structured comparisons or data.",
                "Use real tables with headers or captions for important comparative data.",
            )
        ratio = doc.data_tables / doc.tables
        detail = f"{doc.data_tables}/{doc.tables} table(s) include header cells or captions."
        fix = (
            ""
            if ratio >= 0.999
            else "Use <th> cells or a <caption> so engines can parse table meaning."
        )
        return result(self, ratio, detail, fix)


class CanonicalRule(BaseRule):
    id = "canonical"
    title = "Canonical URL"
    category = Category.MULTIMEDIA
    weight = 1.0

    def check(self, doc: Document) -> RuleResult:
        if doc.canonical:
            return result(self, 1.0, "Canonical URL is declared.", "")
        return result(
            self,
            0.0,
            "No canonical link found.",
            'Add <link rel="canonical" href="..."> to consolidate duplicate URLs.',
        )


class SocialCardRule(BaseRule):
    id = "social-card"
    title = "Social card metadata"
    category = Category.MULTIMEDIA
    weight = 1.0

    def check(self, doc: Document) -> RuleResult:
        og_keys = ("og:title", "og:description", "og:image")
        present_og = [key for key in og_keys if doc.meta.get(key)]
        has_twitter = bool(doc.meta.get("twitter:card"))
        if len(present_og) == len(og_keys) or has_twitter:
            detail = (
                "Open Graph card is complete."
                if len(present_og) == len(og_keys)
                else "Twitter card metadata is present."
            )
            return result(self, 1.0, detail, "")
        if present_og:
            return result(
                self,
                len(present_og) / len(og_keys),
                f"Partial Open Graph metadata present: {', '.join(present_og)}.",
                "Add og:title, og:description, and og:image, or a twitter:card meta tag.",
            )
        return result(
            self,
            0.0,
            "No Open Graph or Twitter card metadata found.",
            "Add Open Graph or Twitter card tags so answer surfaces can preview the page.",
        )
