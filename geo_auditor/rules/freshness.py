"""Freshness rule: engines down-rank undated, stale-looking content."""

from __future__ import annotations

from geo_auditor.models import Category, Document, RuleResult
from geo_auditor.rules.base import BaseRule, result

# A fixed reference year keeps the rule deterministic and CI-stable. Bump it on
# release rather than reading the system clock (which would break reproducible
# tests and reports).
REFERENCE_YEAR = 2026
_RECENT_YEARS = {str(REFERENCE_YEAR), str(REFERENCE_YEAR - 1)}


class FreshnessRule(BaseRule):
    id = "freshness-signal"
    title = "Freshness signal"
    category = Category.FRESHNESS
    weight = 3.0

    def check(self, doc: Document) -> RuleResult:
        has_iso = any(
            key in doc.meta for key in ("article:modified_time", "article:published_time")
        )
        has_schema_date = any(
            block.get("dateModified") or block.get("datePublished") for block in doc.json_ld
        )
        recent = any(any(y in d for y in _RECENT_YEARS) for d in doc.dates)

        if (has_iso or has_schema_date) and recent:
            return result(
                self,
                1.0,
                "Machine-readable date present and recent.",
                "",
            )
        if has_iso or has_schema_date:
            return result(
                self,
                0.7,
                "A machine-readable date exists but is not recent.",
                "Refresh the content and update dateModified.",
            )
        if doc.dates:
            return result(
                self,
                0.5,
                "A date appears in the text but not in metadata.",
                "Expose the date via meta tags or schema.org dateModified.",
            )
        return result(
            self,
            0.0,
            "No date or freshness signal found.",
            "Show a visible 'last updated' date and a schema.org dateModified.",
        )
