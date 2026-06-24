# geo-auditor

**Will ChatGPT, Perplexity, Gemini, and Google AI Overviews cite your page? Find out in one command.**

`geo-auditor` scores any web page for **GEO** (Generative Engine Optimization) and
**AEO** (Answer Engine Optimization): the on-page signals that decide whether an
AI answer engine quotes you or your competitor. It is **keyless, offline, and
deterministic** - point it at an HTML or Markdown file (or a URL) and get a
0-100 score plus a prioritized list of fixes.

No API keys. No tracking. No account. Just a score and a to-do list.

```text
$ geo-audit check article.html

GEO/AEO readiness report
========================
Score: 64/100  (grade D)

By category:
  structure        80/100
  machine-readable  35/100
  authority         50/100
  freshness          0/100

Checks (worst first):
  [FAIL] Schema.org structured data (json-ld-schema) - 0%
        No JSON-LD structured data found.
        fix: Add a schema.org JSON-LD block (Article, FAQPage or HowTo) so engines can read the page as data.
  [FAIL] Freshness signal (freshness-signal) - 0%
        No date or freshness signal found.
        fix: Show a visible 'last updated' date and a schema.org dateModified.
  [WARN] Statistics with citations (statistics-cited) - 50%
        3 stat(s) present but none are backed by an outbound source.
        fix: Cite a source link next to each key statistic.
  ...
```

## Why this exists

AI answer engines now sit between your content and your reader. They lift
answers from pages that are **structured, citable, and machine-readable**, and
they ignore the rest. The research is clear: in the
[GEO paper (Aggarwal et al., KDD 2024)](https://arxiv.org/abs/2311.09735),
adding citations, statistics, and clear structure lifted a page's visibility in
generative engines by up to 40%.

Most teams have no idea where they stand. `geo-auditor` turns that into a number
and a checklist you can act on today - and ship as a CI gate so pages never
regress.

## Install

```bash
pip install geo-auditor
```

That is the whole setup. Python 3.11+.

## Usage

```bash
# Audit a local file or a live URL
geo-audit check article.html
geo-audit check https://yoursite.com/post

# Machine-readable output
geo-audit check article.html --format json
geo-audit check article.html --format md

# Use it as a CI gate (exits non-zero below the threshold)
geo-audit check article.html --min-score 70

# List every rule and its weight
geo-audit rules

# Generate a starter llms.txt for your site
geo-audit init-llms index.html --site-name "Your Brand"
```

### Use it in CI

```yaml
- run: pip install geo-auditor
- run: geo-audit check dist/index.html --min-score 75
```

### Use it as a library

```python
from geo_auditor import parse_content, build_report, render_markdown

doc = parse_content(open("article.html").read(), fmt="html")
report = build_report(doc)
print(report.score, report.grade)
print(render_markdown(report))
```

## What it checks (14 rules, 4 pillars)

| Pillar | Rule | What it rewards |
| --- | --- | --- |
| Structure | `answer-first` | A concise, liftable answer in the opening paragraph |
| Structure | `question-headings` | Headings phrased as the questions users ask |
| Structure | `scannable` | Short paragraphs and lists, not walls of text |
| Structure | `heading-hierarchy` | One H1, no skipped heading levels |
| Structure | `content-depth` | Enough substance to be worth quoting |
| Structure | `tldr-summary` | An extractable TL;DR / key-takeaways block |
| Machine-readable | `json-ld-schema` | schema.org structured data (Article/FAQ/HowTo) |
| Machine-readable | `faq` | FAQ section with FAQPage schema |
| Machine-readable | `meta-tags` | Well-sized title and meta description |
| Machine-readable | `entity-clarity` | Title and H1 aligned on one clear topic |
| Authority | `statistics-cited` | Concrete stats backed by sources |
| Authority | `outbound-citations` | Links to authoritative sources |
| Authority | `author-eeat` | A named author (E-E-A-T signal) |
| Freshness | `freshness-signal` | A visible, machine-readable date |

Run `geo-audit rules` to see weights. Every rule returns a score, a plain-English
reason, and a concrete fix.

## How scoring works

Each rule returns a 0.0-1.0 score. The overall score is a weighted average
mapped to a letter grade (A 90+, B 80+, C 70+, D 60+, F below). It is fully
deterministic: the same page always produces the same score, so it is safe to
diff in CI. The freshness rule uses a fixed reference year (bumped per release)
rather than the system clock, so reports are reproducible.

## FAQ

**Does it call ChatGPT/Perplexity to check rankings?** No. It analyzes the
*on-page* signals those engines are known to favor. It is fully offline (URL
fetching uses only the Python standard library and is optional), which keeps it
free, fast, and deterministic.

**Is this just SEO?** Overlapping but different. Classic SEO optimizes for the
ten blue links; GEO/AEO optimizes for being *quoted inside an AI answer* -
structured data, citable facts, and answer-first writing matter much more.

**Is `geo-audit` the first GEO tool?** No - it is an open, scriptable, keyless
one. Hosted trackers (Profound, Otterly, and others) query live engines; this
audits the page itself, for free, in your terminal and CI.

## Roadmap

- More schema types and an HTML-rendering check
- Sitemap crawling for whole-site reports
- A hosted dashboard with live answer-engine tracking - part of
  [Trawlkit](https://github.com/baronguyen001), the toolkit this is a piece of

## Contributing

Issues and PRs welcome. `pip install -e ".[dev]"`, then `ruff check .`,
`mypy geo_auditor`, and `pytest`.

## License

MIT (c) 2026 baronguyen001. See [LICENSE](LICENSE).
