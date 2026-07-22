"""Tests for individual rules and the rule registry."""

from __future__ import annotations

from geo_auditor.models import Category, Document, Severity
from geo_auditor.parse import parse_content
from geo_auditor.rules import ALL_RULES, audit
from geo_auditor.rules.authority import AuthorRule, CitationsRule, StatisticsRule
from geo_auditor.rules.freshness import FreshnessRule
from geo_auditor.rules.machine import (
    EntityClarityRule,
    FaqRule,
    JsonLdRule,
    MetaTagsRule,
)
from geo_auditor.rules.multimedia import (
    AltTextRule,
    CanonicalRule,
    SocialCardRule,
    TableDataRule,
)
from geo_auditor.rules.readability import (
    DescriptiveAnchorRule,
    ParagraphLengthRule,
    SentenceLengthRule,
)
from geo_auditor.rules.structure import (
    AnswerFirstRule,
    ContentDepthRule,
    HeadingHierarchyRule,
    QuestionHeadingsRule,
    ScannableRule,
    TldrSummaryRule,
)


def test_registry_has_21_rules() -> None:
    assert len(ALL_RULES) == 21
    ids = [r.id for r in ALL_RULES]
    assert len(ids) == len(set(ids)), "rule ids must be unique"
    assert any(r.category is Category.READABILITY for r in ALL_RULES)


def test_audit_returns_one_result_per_rule(strong_doc: Document) -> None:
    results = audit(strong_doc)
    assert len(results) == len(ALL_RULES)


def test_strong_doc_mostly_passes(strong_doc: Document) -> None:
    results = audit(strong_doc)
    passed = [r for r in results if r.severity is Severity.PASS]
    assert len(passed) >= 16


def test_weak_doc_mostly_fails(weak_doc: Document) -> None:
    results = audit(weak_doc)
    failed = [r for r in results if r.severity is Severity.FAIL]
    assert len(failed) >= 7


def test_answer_first_variants() -> None:
    short = Document(paragraphs=["too short"])
    assert AnswerFirstRule().check(short).severity is Severity.WARN
    empty = Document(paragraphs=[])
    assert empty.paragraphs == []
    assert AnswerFirstRule().check(empty).severity is Severity.FAIL
    long_para = Document(paragraphs=[" ".join(["word"] * 200)])
    assert AnswerFirstRule().check(long_para).score == 0.5
    good = Document(paragraphs=[" ".join(["word"] * 40)])
    assert AnswerFirstRule().check(good).passed


def test_question_headings_none() -> None:
    doc = Document()
    assert QuestionHeadingsRule().check(doc).severity is Severity.FAIL


def test_scannable_no_paragraphs() -> None:
    assert ScannableRule().check(Document()).severity is Severity.FAIL


def test_heading_hierarchy_detects_skips() -> None:
    from geo_auditor.models import Heading

    skipped = Document(headings=[Heading(1, "a"), Heading(3, "b")])
    res = HeadingHierarchyRule().check(skipped)
    assert res.score < 1.0
    none = Document()
    assert HeadingHierarchyRule().check(none).severity is Severity.FAIL


def test_content_depth_bands() -> None:
    assert ContentDepthRule().check(Document(text="w " * 400)).passed
    assert ContentDepthRule().check(Document(text="w " * 200)).score == 0.5
    assert ContentDepthRule().check(Document(text="w " * 10)).severity is Severity.FAIL


def test_tldr_rule() -> None:
    assert TldrSummaryRule().check(Document(has_summary=True)).passed
    assert TldrSummaryRule().check(Document(has_summary=False)).severity is Severity.FAIL


def test_jsonld_relevant_vs_irrelevant() -> None:
    relevant = Document(json_ld=[{"@type": "Article"}])
    assert JsonLdRule().check(relevant).passed
    irrelevant = Document(json_ld=[{"@type": "Organization"}])
    assert JsonLdRule().check(irrelevant).score == 0.5
    assert JsonLdRule().check(Document()).severity is Severity.FAIL


def test_faq_rule_levels() -> None:
    schema = Document(json_ld=[{"@type": "FAQPage"}])
    assert FaqRule().check(schema).passed
    section = Document(has_faq=True)
    assert FaqRule().check(section).score == 0.6
    assert FaqRule().check(Document()).severity is Severity.FAIL


def test_meta_tags_rule() -> None:
    good = Document(title="A reasonably sized page title here", meta={"description": "d" * 100})
    assert MetaTagsRule().check(good).passed
    assert MetaTagsRule().check(Document(title="x")).severity is Severity.FAIL


def test_entity_clarity_rule() -> None:
    aligned = Document(title="Cold Brew Coffee Guide", h1="Cold Brew Coffee Guide")
    assert EntityClarityRule().check(aligned).passed
    missing = Document(title="", h1="")
    assert EntityClarityRule().check(missing).severity is Severity.FAIL
    no_keywords = Document(title="the a an", h1="of to in")
    assert EntityClarityRule().check(no_keywords).score == 0.5


def test_statistics_rule() -> None:
    from geo_auditor.models import Link

    no_stats = Document(text="no numbers here at all")
    assert StatisticsRule().check(no_stats).severity is Severity.FAIL
    stats_no_cite = Document(text="we grew 40% and saved 200 hours")
    assert StatisticsRule().check(stats_no_cite).score == 0.5
    cited = Document(
        text="we grew 40% last year",
        links=[Link("https://a.com", "a", True), Link("https://b.com", "b", True)],
    )
    assert StatisticsRule().check(cited).passed


def test_citations_rule() -> None:
    from geo_auditor.models import Link

    two = Document(links=[Link("https://a.com", "a", True), Link("https://b.com", "b", True)])
    assert CitationsRule().check(two).passed
    one = Document(links=[Link("https://a.com", "a", True)])
    assert CitationsRule().check(one).score == 0.5
    assert CitationsRule().check(Document()).severity is Severity.FAIL


def test_author_rule() -> None:
    meta = Document(meta={"author": "Jane Doe"})
    assert AuthorRule().check(meta).passed
    schema = Document(json_ld=[{"author": {"name": "Jane"}}])
    assert AuthorRule().check(schema).passed
    byline = Document(text="Written by Jane and reviewed carefully")
    assert AuthorRule().check(byline).score == 0.6
    assert AuthorRule().check(Document()).severity is Severity.FAIL


def test_freshness_rule_levels() -> None:
    recent = Document(meta={"article:modified_time": "2026-01-01"}, dates=["2026-01-01"])
    assert FreshnessRule().check(recent).passed
    old_iso = Document(meta={"article:modified_time": "2019-01-01"}, dates=["2019-01-01"])
    assert FreshnessRule().check(old_iso).score == 0.7
    text_only = Document(dates=["2020"])
    assert FreshnessRule().check(text_only).score == 0.5
    assert FreshnessRule().check(Document()).severity is Severity.FAIL


def test_alt_text_rule() -> None:
    from geo_auditor.models import Image

    good = Document(images=[Image(src="/a.jpg", alt="Useful chart")])
    assert AltTextRule().check(good).passed
    partial = Document(
        images=[Image(src="/a.jpg", alt="Useful chart"), Image(src="/b.jpg", alt="")]
    )
    assert partial.images[1].alt == ""
    assert AltTextRule().check(partial).score == 0.5
    assert AltTextRule().check(Document()).severity is Severity.FAIL


def test_table_data_rule() -> None:
    assert TableDataRule().check(Document(tables=2, data_tables=2)).passed
    assert TableDataRule().check(Document(tables=2, data_tables=1)).score == 0.5
    assert TableDataRule().check(Document()).severity is Severity.FAIL


def test_canonical_rule() -> None:
    assert CanonicalRule().check(Document(canonical="https://example.com/page")).passed
    assert CanonicalRule().check(Document()).severity is Severity.FAIL


def test_social_card_rule() -> None:
    og = Document(
        meta={
            "og:title": "Title",
            "og:description": "Description",
            "og:image": "https://example.com/image.jpg",
        }
    )
    assert SocialCardRule().check(og).passed
    twitter = Document(meta={"twitter:card": "summary_large_image"})
    assert SocialCardRule().check(twitter).passed
    partial = Document(meta={"og:title": "Title"})
    assert SocialCardRule().check(partial).score == 1 / 3
    assert SocialCardRule().check(Document()).severity is Severity.FAIL


def test_multimedia_rules_on_markdown_input(weak_doc: Document) -> None:
    for rule in (AltTextRule(), TableDataRule(), CanonicalRule(), SocialCardRule()):
        assert rule.check(weak_doc).severity is Severity.FAIL


def test_sentence_length_rule_scores_concise_long_and_empty_text() -> None:
    rule = SentenceLengthRule()
    concise = Document(text="Short answers help. Clear writing is easy to cite.")
    long_sentence = Document(text=" ".join(["word"] * 45) + ".")

    assert rule.check(concise).passed
    assert rule.check(long_sentence).severity is Severity.FAIL
    assert rule.check(Document()).severity is Severity.FAIL
    assert "No sentence text" in rule.check(Document()).detail


def test_paragraph_length_rule_scores_concise_long_and_empty_paragraphs() -> None:
    rule = ParagraphLengthRule()
    concise = Document(paragraphs=[" ".join(["word"] * 40), " ".join(["word"] * 60)])
    long_para = Document(paragraphs=[" ".join(["word"] * 170)])

    assert rule.check(concise).passed
    assert rule.check(long_para).severity is Severity.FAIL
    assert rule.check(Document()).severity is Severity.FAIL
    assert "No paragraphs" in rule.check(Document()).detail


def test_descriptive_anchor_rule_scores_generic_descriptive_and_no_links() -> None:
    from geo_auditor.models import Link

    rule = DescriptiveAnchorRule()
    mixed = Document(
        links=[
            Link("https://example.com/a", "cold brew ratio study", True),
            Link("https://example.com/b", "read more", True),
            Link("https://example.com/c", "", True),
        ]
    )
    no_links = rule.check(Document())

    assert rule.check(Document(links=[Link("https://example.com/a", "source data", True)])).passed
    assert rule.check(mixed).score == 1 / 3
    assert no_links.passed
    assert no_links.detail == "No links to evaluate."


def test_every_category_represented() -> None:
    categories = {r.category for r in ALL_RULES}
    assert categories == set(Category)


def test_rules_are_deterministic(strong_html: str) -> None:
    a = audit(parse_content(strong_html, fmt="html"))
    b = audit(parse_content(strong_html, fmt="html"))
    assert [(r.rule_id, r.score) for r in a] == [(r.rule_id, r.score) for r in b]
