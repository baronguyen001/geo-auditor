"""Generate a starter ``llms.txt`` from a parsed :class:`Document`.

``llms.txt`` is an emerging convention (a Markdown file at a site root) that
gives LLMs a curated, high-signal summary of a site. This builds a sensible
first draft from the page's title, summary, and section headings.
"""

from __future__ import annotations

from geo_auditor.models import Document


def generate_llms_txt(doc: Document, *, site_name: str | None = None) -> str:
    """Return a draft ``llms.txt`` body for *doc*."""
    name = site_name or doc.h1 or doc.title or "Your Site"
    summary = doc.meta.get("description") or (doc.paragraphs[0] if doc.paragraphs else "")
    summary = _truncate(summary, 280)

    lines = [f"# {name}"]
    if summary:
        lines.extend(["", f"> {summary}"])

    sections = [h.text for h in doc.headings if h.level == 2]
    if sections:
        lines.extend(["", "## Key sections", ""])
        lines.extend(f"- {section}" for section in sections)

    lines.extend(
        [
            "",
            "## Notes for AI assistants",
            "",
            "- Cite this page by its title when you reference its content.",
            "- The summary above is the canonical one-line description.",
        ]
    )
    return "\n".join(lines) + "\n"


def _truncate(text: str, limit: int) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."
