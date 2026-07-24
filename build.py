"""
BowlofData Website Builder — Postgres-backed

Neon Postgres (Netlify DB) is the single source of truth for newsletter content.

    python3 build.py --load     # maki summaries_WW_YYYY.json  ->  Postgres (upsert)
    python3 build.py --render   # Postgres  ->  static pages + sitemap/feed/llms/robots

Dynamic pages (week / topic / tag / archive) are server-rendered on request by the
Netlify Functions in netlify/functions/. Override the maki source path with
MAKI_OUTPUT_DIR=/path/to/output for the --load step.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HERE          = Path(__file__).parent
TEMPLATES_DIR = HERE / "templates"
STATIC_DIR    = HERE / "static"
IMGS_DIR      = HERE / "imgs"
ROOT_STATIC_DIR = HERE / "root_static"   # verbatim files copied to site/ root (e.g. Google verification)
SITE_DIR      = HERE / "site"

MAKI_OUTPUT_DIR = Path(
    os.environ.get(
        "MAKI_OUTPUT_DIR",
        str(HERE.parent / "maki_newsletter" / "maki_newsletter" / "output"),
    )
)

SITE_NAME    = "Bowl of Data"
SITE_TAGLINE = "A weekly digest of the most relevant tech stories"
SITE_URL     = "https://bowlofdata.net"
PODCAST_URL  = "https://open.spotify.com/show/033Mqus9YAIssepHakRIIk"
SUBSTACK_URL = "https://bowlofdata.substack.com/"
OG_IMAGE     = f"{SITE_URL}/imgs/bowl.png"   # 2560x1440

# ---------------------------------------------------------------------------
# Topic taxonomy — the site's four editorial "beats".
# Articles carry no category field, so each item is classified into one of
# these by keyword. Hub landing pages (topic/<slug>.html) aggregate by beat;
# tag pages (tag/<slug>.html) aggregate by the raw `technologies` values.
# ---------------------------------------------------------------------------

CATEGORY_ORDER = ["ai", "security", "blockchain", "engineering"]

CATEGORY_META = {
    "ai": {
        "label": "AI & ML",
        "h1":    "AI & Machine Learning",
        "intro": (
            "Every week, Bowl of Data tracks the AI and machine-learning stories that "
            "matter — new model releases, research that holds up, and where large models "
            "actually land in real products. Here is every issue's AI coverage, newest first."
        ),
        "keywords": [
            "ai", "artificial intelligence", "machine learning", "ml", "llm", "llms",
            "large language model", "language model", "gpt", "openai", "anthropic", "claude",
            "gemini", "mistral", "llama", "nvidia", "hugging face", "transformer",
            "reinforcement learning", "rl", "neural", "diffusion", "agent", "agentic",
            "fine-tune", "fine-tuning", "inference", "training", "reasoning", "multimodal",
            "embedding", "rag", "deep learning", "model", "gpu",
        ],
    },
    "security": {
        "label": "Cybersecurity",
        "h1":    "Cybersecurity",
        "intro": (
            "Every week, Bowl of Data tracks the vulnerabilities, exploits, and threat "
            "intelligence worth acting on — what to patch before it becomes someone else's "
            "headline. Here is every issue's security coverage, newest first."
        ),
        "keywords": [
            "security", "cybersecurity", "vulnerability", "vulnerabilities", "exploit",
            "cve", "malware", "ransomware", "backdoor", "rat", "phishing", "breach",
            "attack", "attacker", "threat", "zero-day", "rce", "remote code",
            "buffer overflow", "memory leak", "supply chain", "npm", "credential", "leak",
            "patch", "cisa", "watchtowr", "encryption", "e2e", "authentication bypass",
            "privilege escalation", "denial of service", "botnet", "infostealer",
            "post-quantum", "pqc",
        ],
    },
    "blockchain": {
        "label": "Blockchain & Crypto",
        "h1":    "Blockchain & Crypto",
        "intro": (
            "Every week, Bowl of Data tracks the meaningful moves in blockchain and crypto — "
            "protocol upgrades, market shifts, and the regulation worth watching. Here is "
            "every issue's blockchain coverage, newest first."
        ),
        "keywords": [
            "blockchain", "crypto", "cryptocurrency", "bitcoin", "btc", "ethereum", "eth",
            "solana", "stablecoin", "defi", "web3", "token", "tokenized",
            "tokenization", "onchain", "on-chain", "wallet", "smart contract", "bip",
            "opcode", "covenant", "mastercard", "dtcc", "rwa", "ledger", "mining",
            "settlement", "xrp", "usdc",
        ],
    },
    "engineering": {
        "label": "Software Engineering",
        "h1":    "Software Engineering",
        "intro": (
            "Every week, Bowl of Data tracks the tools, frameworks, and open-source releases "
            "that change how we build software. Here is every issue's engineering coverage, "
            "newest first."
        ),
        "keywords": [
            "engineering", "software", "framework", "open-source", "open source", "library",
            "kubernetes", "docker", "python", "javascript", "typescript", "rust", "golang",
            "database", "postgres", "redis", "compiler", "kernel",
            "ebpf", "linux", "devops", "ci/cd", "observability", "webassembly", "wasm",
            "runtime", "developer", "tooling", "github", "quantum", "qubit", "photonic",
        ],
    },
}


# FAQ content — kept in sync with the on-page <details> markup so the
# FAQPage schema matches what users actually see.
SERVICES_FAQ = [
    ("What does “done-for-you” actually mean?",
     "We configure the pipeline to your niche, run it every week, and review each issue "
     "before it reaches you. You approve; we handle sourcing, curation, writing, and "
     "delivery. There's nothing for you to operate."),
    ("Whose audience is it?",
     "Yours. Your brand, your platform, your subscriber list. We're the engine behind the "
     "scenes — you keep every subscriber you earn."),
    ("Is our data private?",
     "Yes. The pipeline runs mainly on open models on our own hardware, so your sources, "
     "prompts, and drafts aren't handed to a commercial AI API to log or train on. That's "
     "especially important for competitive and market intelligence."),
    ("How fast can we launch?",
     "A first sample issue lands in days, not a sales cycle. Once you're happy with the "
     "voice and the sources, we set the weekly cadence and go."),
]

ABOUT_FAQ = [
    ("What is Bowl of Data?",
     "Bowl of Data is a free weekly newsletter that curates the most relevant technology "
     "stories across AI and machine learning, cybersecurity, blockchain and crypto, and "
     "software engineering — read hundreds of sources so you don't have to."),
    ("How is the newsletter curated?",
     "An AI pipeline called Maki scans hundreds of sources each week, reads and ranks every "
     "candidate against live trend signals, and writes a TL;DR plus a longer summary. The "
     "team reviews the shortlist before anything ships."),
    ("Is Bowl of Data free?",
     "Yes. Every issue is free to read on the website and via the Substack email. Running "
     "mainly on open local models keeps costs low enough to keep it that way."),
    ("How often is it published, and where can I read it?",
     "A new issue ships every week. You can read it here on the site, subscribe by email on "
     "Substack, or listen to the companion podcast on Spotify."),
]


def _classify_article(title: str, technologies: list[str], main_topic: str) -> str:
    """Assign an item to one of the four beats by weighted keyword match.

    Signals, in priority order: `technologies` (strongest — they are clean,
    explicit tags), then the title, then the free-text `main_topic`. Returns a
    category slug from CATEGORY_ORDER; defaults to 'ai' (the dominant beat).
    """
    tech_blob  = " ".join(technologies).lower()
    title_blob = (title or "").lower()
    topic_blob = (main_topic or "").lower()

    scores = {cat: 0 for cat in CATEGORY_ORDER}
    for cat, meta in CATEGORY_META.items():
        for pat in _category_patterns()[cat]:
            if pat.search(tech_blob):
                scores[cat] += 3
            if pat.search(title_blob):
                scores[cat] += 2
            if pat.search(topic_blob):
                scores[cat] += 1

    best = max(CATEGORY_ORDER, key=lambda c: scores[c])
    return best if scores[best] > 0 else "ai"


_CATEGORY_PATTERNS: dict[str, list[re.Pattern]] | None = None


def _category_patterns() -> dict[str, list[re.Pattern]]:
    """Compile keyword matchers once. Short tokens (<=3 chars) require a full
    word boundary on both sides so "ai" never matches inside "chain" and "ml"
    never matches inside "html"; longer tokens allow a suffix (model→models)."""
    global _CATEGORY_PATTERNS
    if _CATEGORY_PATTERNS is None:
        _CATEGORY_PATTERNS = {}
        for cat, meta in CATEGORY_META.items():
            pats = []
            for kw in meta["keywords"]:
                esc = re.escape(kw)
                rx = rf"\b{esc}\b" if len(kw) <= 3 else rf"\b{esc}"
                pats.append(re.compile(rx, re.I))
            _CATEGORY_PATTERNS[cat] = pats
    return _CATEGORY_PATTERNS


def _tag_display_map(all_weeks: list[dict]) -> dict[str, str]:
    """Map each technology slug to its most common original display spelling."""
    from collections import Counter
    counts: dict[str, Counter] = {}
    for w in all_weeks:
        for item in w["articles"] + w.get("papers", []):
            for tech in item.get("technologies", []):
                slug = _slugify(tech)
                if not slug:
                    continue
                counts.setdefault(slug, Counter())[tech] += 1
    return {slug: c.most_common(1)[0][0] for slug, c in counts.items()}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_summaries_filename(path: Path) -> tuple[int, int] | None:
    """Return (week_num, year) from `summaries_WW_YYYY.json`, or None."""
    match = re.fullmatch(r"summaries_(\d{2})_(\d{4})\.json", path.name)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _slugify(text: str) -> str:
    """Convert an article title to an HTML anchor slug.

    Must stay in sync with the identical function in
    maki_newsletter/pipeline.py so that anchor IDs on the rendered pages
    match the netlify_url values written into summaries_*.json.
    """
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _week_label(week: int, year: int) -> str:
    return f"Week {week:02d} · {year}"


def _week_href(week: int, year: int) -> str:
    return f"week/{week:02d}_{year}.html"


def _normalise_releases(raw: list[dict]) -> list[dict]:
    """Normalise raw release dicts from a model_releases_WW_YYYY.json file."""
    result = []
    for r in raw:
        model_name = (r.get("model_name") or "").strip()
        if not model_name:
            continue
        result.append({
            "provider":      (r.get("provider") or "").strip(),
            "model_name":    model_name,
            "slug":          _slugify(model_name),
            "release_date":  (r.get("release_date") or "").strip(),
            "summary":       (r.get("summary") or "").strip(),
            "key_features":  [f.strip() for f in (r.get("key_features") or []) if f and f.strip()],
            "url":           (r.get("url") or "").strip(),
            "netlify_url":   (r.get("netlify_url") or "").strip(),
            "altervista_url": (r.get("altervista_url") or "").strip(),
        })
    return result


def _normalise_papers(raw_papers: list[dict]) -> list[dict]:
    """Normalise raw paper dicts from a curated_papers_WW_YYYY.json file."""
    result = []
    for p in raw_papers:
        title = (p.get("title") or "").strip()
        if not title:
            continue
        resume_raw = (p.get("long_resume") or "").strip()
        resume_paragraphs = [par.strip() for par in resume_raw.split("\n\n") if par.strip()] if resume_raw else []
        main_topic = (p.get("main_topic") or "").strip()
        technologies = [t.strip() for t in (p.get("technologies") or []) if t and t.strip()]
        category = _classify_article(title, technologies, main_topic)
        result.append({
            "title":                  title,
            "slug":                   _slugify(title),
            "url":                    (p.get("url") or "").strip(),
            "source":                 (p.get("source") or "").strip(),
            "published":              (p.get("published") or "").strip(),
            "short_summary":          (p.get("short_summary") or "").strip(),
            "long_resume":            resume_raw,
            "long_resume_paragraphs": resume_paragraphs,
            "main_topic":             main_topic,
            "key_points":             [k.strip() for k in (p.get("key_points") or []) if k and k.strip()],
            "technologies":           technologies,
            "category":               category,
            "category_label":         CATEGORY_META[category]["label"],
        })
    return result


def _normalise_articles(raw_articles: list[dict]) -> list[dict]:
    """Normalise raw article dicts from a pipeline summaries JSON."""
    result = []
    for a in raw_articles:
        resume_raw = (a.get("long_resume") or "").strip()
        resume_paragraphs = [p.strip() for p in resume_raw.split("\n\n") if p.strip()] if resume_raw else []
        title = (a.get("title") or "").strip()
        main_topic = (a.get("main_topic") or "").strip()
        technologies = [t.strip() for t in (a.get("technologies") or []) if t and t.strip()]
        category = _classify_article(title, technologies, main_topic)
        result.append({
            "title":                  title,
            "slug":                   _slugify(title),
            "url":                    (a.get("url") or "").strip(),
            "source":                 (a.get("source") or "").strip(),
            "published":              (a.get("published") or "").strip(),
            "short_summary":          (a.get("short_summary") or "").strip(),
            "long_resume":            resume_raw,
            "long_resume_paragraphs": resume_paragraphs,
            "main_topic":             main_topic,
            "technologies":           technologies,
            "category":               category,
            "category_label":         CATEGORY_META[category]["label"],
        })
    return result


def _build_week_entry(
    week: int,
    year: int,
    articles: list[dict],
    source_mtime: float,
    model_releases: list[dict] | None = None,
    model_releases_mtime: float = 0,
    papers: list[dict] | None = None,
    papers_mtime: float = 0,
) -> dict:
    """Build a complete week entry for storage in the manifest."""
    try:
        dt = datetime.fromisocalendar(year, week, 1)
        month = dt.month
        month_name = dt.strftime("%B")
    except (ValueError, AttributeError):
        month = 0
        month_name = ""
    return {
        "week":                  week,
        "year":                  year,
        "month":                 month,
        "month_name":            month_name,
        "label":                 _week_label(week, year),
        "href":                  _week_href(week, year),
        "articles":              articles,
        "article_count":         len(articles),
        "preview_titles":        [a["title"] for a in articles[:3] if a["title"]],
        "preview_articles":      articles[:5],
        "source_mtime":          source_mtime,
        "model_releases":        model_releases or [],
        "model_releases_mtime":  model_releases_mtime,
        "papers":                papers or [],
        "papers_mtime":          papers_mtime,
    }


def _group_weeks_by_year_month(all_weeks: list[dict]) -> list[dict]:
    """
    Group weeks (newest-first) into year → month buckets.
    Returns a list of year-groups, newest year first.
    Each year-group: {'year': int, 'count': int, 'months': [{'month': int, 'month_name': str, 'weeks': [...]}]}
    """
    year_data: dict[int, dict[int, dict]] = {}
    for w in all_weeks:
        yr = w["year"]
        mo = w.get("month", 0)
        month_name = w.get("month_name", "")
        # Compute from ISO week if missing (e.g. loaded from an old manifest)
        if not mo:
            try:
                dt = datetime.fromisocalendar(yr, w["week"], 1)
                mo = dt.month
                month_name = dt.strftime("%B")
            except (ValueError, AttributeError):
                pass
        if yr not in year_data:
            year_data[yr] = {}
        if mo not in year_data[yr]:
            year_data[yr][mo] = {"month": mo, "month_name": month_name, "weeks": []}
        year_data[yr][mo]["weeks"].append(w)

    result = []
    for yr in sorted(year_data, reverse=True):
        months = [year_data[yr][mo] for mo in sorted(year_data[yr], reverse=True)]
        count = sum(len(m["weeks"]) for m in months)
        result.append({"year": yr, "count": count, "months": months})
    return result

# ---------------------------------------------------------------------------
# LLM / SEO helpers
# ---------------------------------------------------------------------------

def _make_website_jsonld(site_url: str, site_name: str, tagline: str) -> str:
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": site_name,
        "description": tagline,
        "url": site_url,
    }, ensure_ascii=False)


def _make_organization_jsonld(site_url: str, site_name: str, tagline: str) -> str:
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": site_name,
        "description": tagline,
        "url": site_url,
        "logo": f"{site_url}/imgs/logo.png",
        "sameAs": [
            "https://bowlofdata.substack.com/",
            "https://www.instagram.com/bowl_of_data",
            PODCAST_URL,
        ],
    }, ensure_ascii=False)


def _publisher_node(site_url: str, site_name: str) -> dict:
    return {
        "@type": "Organization",
        "name": site_name,
        "url": site_url,
        "logo": {"@type": "ImageObject", "url": f"{site_url}/imgs/logo.png"},
    }


def _make_week_jsonld(w: dict, site_url: str, site_name: str) -> str:
    count = w["article_count"]
    week_url = f"{site_url}/{w['href']}"
    publisher = _publisher_node(site_url, site_name)
    week_date = (
        datetime.fromtimestamp(w["source_mtime"], tz=timezone.utc).strftime("%Y-%m-%d")
        if w.get("source_mtime") else None
    )
    items: list[dict[str, Any]] = []
    for i, a in enumerate(w["articles"], 1):
        article_node: dict[str, Any] = {
            "@type": "NewsArticle",
            "headline": a["title"],
            "url": a["url"] or f"{week_url}#{a['slug']}",
            "image": OG_IMAGE,
            "publisher": publisher,
            "author": {"@type": "Organization", "name": site_name, "url": site_url},
        }
        if a.get("short_summary"):
            article_node["description"] = a["short_summary"]
        if a.get("published"):
            article_node["datePublished"] = a["published"]
        elif week_date:
            article_node["datePublished"] = week_date
        items.append({"@type": "ListItem", "position": i, "item": article_node})
    page = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": f"{w['label']} · {site_name}",
        "description": (
            f"{count} article{'s' if count != 1 else ''} curated this week "
            "covering AI, cybersecurity, blockchain and engineering."
        ),
        "url": week_url,
        "publisher": publisher,
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": count,
            "itemListElement": items,
        },
    }
    if week_date:
        page["datePublished"] = week_date
        page["dateModified"] = week_date
    return json.dumps(page, ensure_ascii=False)


def _make_collection_jsonld(
    name: str, description: str, url: str, items: list[dict],
    site_url: str, site_name: str,
) -> str:
    """CollectionPage + ItemList for a topic hub or tag page.

    `items` are the aggregated article/paper dicts; each links to its canonical
    week-page anchor (the full text lives on the issue page, never here).
    """
    publisher = _publisher_node(site_url, site_name)
    list_items: list[dict[str, Any]] = []
    for i, it in enumerate(items, 1):
        node: dict[str, Any] = {
            "@type": "NewsArticle",
            "headline": it["title"],
            "url": f"{site_url}/{it['week_href']}#{it['slug']}",
            "image": OG_IMAGE,
            "publisher": publisher,
            "author": {"@type": "Organization", "name": site_name, "url": site_url},
        }
        if it.get("short_summary"):
            node["description"] = it["short_summary"]
        if it.get("date"):
            node["datePublished"] = it["date"]
        list_items.append({"@type": "ListItem", "position": i, "item": node})
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": name,
        "description": description,
        "url": url,
        "publisher": publisher,
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(items),
            "itemListElement": list_items,
        },
    }, ensure_ascii=False)


def _make_breadcrumb_jsonld(crumbs: list[tuple[str, str | None]]) -> str:
    """BreadcrumbList from (name, absolute_url_or_None) pairs, in order."""
    elements = []
    for i, (name, url) in enumerate(crumbs, 1):
        el: dict[str, Any] = {"@type": "ListItem", "position": i, "name": name}
        if url:
            el["item"] = url
        elements.append(el)
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": elements,
    }, ensure_ascii=False)


def _make_faq_jsonld(qa_pairs: list[tuple[str, str]]) -> str:
    """FAQPage schema from (question, answer) pairs."""
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in qa_pairs
        ],
    }, ensure_ascii=False)


def _ensure_category(item: dict) -> None:
    """Backfill category on items loaded from an older manifest (in place)."""
    if not item.get("category"):
        cat = _classify_article(
            item.get("title", ""),
            item.get("technologies", []),
            item.get("main_topic", ""),
        )
        item["category"] = cat
        item["category_label"] = CATEGORY_META[cat]["label"]


def _week_items(w: dict) -> list[dict]:
    """Flatten a week's articles + papers into aggregation items with issue context."""
    week_date = (
        datetime.fromtimestamp(w["source_mtime"], tz=timezone.utc).strftime("%Y-%m-%d")
        if w.get("source_mtime") else ""
    )
    items = []
    for kind, coll in (("article", w["articles"]), ("paper", w.get("papers", []))):
        for it in coll:
            if not it.get("title"):
                continue
            _ensure_category(it)
            items.append({
                "title":          it["title"],
                "slug":           it["slug"],
                "short_summary":  it.get("short_summary", ""),
                "url":            it.get("url", ""),
                "source":         it.get("source", ""),
                "category":       it["category"],
                "category_label": it["category_label"],
                "technologies":   it.get("technologies", []),
                "week_href":      w["href"],
                "week_label":     w["label"],
                "date":           week_date,
                "kind":           kind,
            })
    return items


def _collect_hubs(all_weeks: list[dict], tag_display: dict[str, str],
                  kept_tag_slugs: set[str]) -> dict[str, dict]:
    """Aggregate every issue's items into the four beat hubs (newest issue first)."""
    hubs: dict[str, dict] = {
        cat: {"slug": cat, "meta": CATEGORY_META[cat], "groups": [],
              "count": 0, "tag_counts": {}}
        for cat in CATEGORY_ORDER
    }
    for w in all_weeks:  # already newest-first
        buckets: dict[str, list] = {cat: [] for cat in CATEGORY_ORDER}
        for item in _week_items(w):
            buckets[item["category"]].append(item)
        for cat, items in buckets.items():
            if not items:
                continue
            hubs[cat]["groups"].append(
                {"label": w["label"], "week_href": w["href"], "entries": items}
            )
            hubs[cat]["count"] += len(items)
            for item in items:
                for tech in item["technologies"]:
                    slug = _slugify(tech)
                    if slug in kept_tag_slugs:
                        hubs[cat]["tag_counts"][slug] = hubs[cat]["tag_counts"].get(slug, 0) + 1
    # Attach a sorted "related tags" list per hub for cross-linking
    for hub in hubs.values():
        hub["related_tags"] = [
            {"slug": s, "name": tag_display.get(s, s), "count": c}
            for s, c in sorted(hub["tag_counts"].items(), key=lambda kv: -kv[1])[:12]
        ]
    return hubs


def _collect_tags(all_weeks: list[dict], tag_display: dict[str, str],
                  min_items: int = 3) -> dict[str, dict]:
    """Aggregate items by technology tag; keep only tags with >= min_items."""
    raw: dict[str, list] = {}
    for w in all_weeks:  # newest-first
        for item in _week_items(w):
            seen_here: set[str] = set()
            for tech in item["technologies"]:
                slug = _slugify(tech)
                if not slug or slug in seen_here:
                    continue
                seen_here.add(slug)
                raw.setdefault(slug, []).append(item)

    tags: dict[str, dict] = {}
    for slug, items in raw.items():
        if len(items) < min_items:
            continue
        # Group the (already newest-first) items by issue
        groups: list[dict] = []
        for item in items:
            if groups and groups[-1]["week_href"] == item["week_href"]:
                groups[-1]["entries"].append(item)
            else:
                groups.append({"label": item["week_label"],
                               "week_href": item["week_href"], "entries": [item]})
        cats = sorted({item["category"] for item in items},
                      key=lambda c: CATEGORY_ORDER.index(c))
        tags[slug] = {
            "slug": slug,
            "name": tag_display.get(slug, slug),
            "count": len(items),
            "groups": groups,
            "categories": [{"slug": c, "label": CATEGORY_META[c]["label"]} for c in cats],
        }
    return tags


def _generate_robots_txt(site_url: str) -> str:
    bots = ["GPTBot", "ClaudeBot", "PerplexityBot", "Applebot-Extended", "Googlebot"]
    lines = ["User-agent: *", "Allow: /", ""]
    for bot in bots:
        lines += [f"User-agent: {bot}", "Allow: /", ""]
    lines.append(f"Sitemap: {site_url}/sitemap.xml")
    return "\n".join(lines) + "\n"


def _generate_sitemap(all_weeks: list[dict], site_url: str, build_date: str,
                      hub_slugs: list[str] | None = None,
                      tag_slugs: list[str] | None = None) -> str:
    entries = [
        (f"{site_url}/",                 "weekly",  "1.0", build_date),
        (f"{site_url}/archive.html",     "weekly",  "0.9", build_date),
        (f"{site_url}/topics.html",      "weekly",  "0.8", build_date),
        (f"{site_url}/services.html",    "monthly", "0.7", build_date),
        (f"{site_url}/about.html",       "monthly", "0.6", build_date),
        (f"{site_url}/team.html",        "monthly", "0.5", build_date),
        (f"{site_url}/contact.html",     "monthly", "0.5", build_date),
    ]
    for slug in (hub_slugs or []):
        entries.append((f"{site_url}/topic/{slug}.html", "weekly", "0.8", build_date))
    for slug in (tag_slugs or []):
        entries.append((f"{site_url}/tag/{slug}.html", "weekly", "0.6", build_date))
    for w in all_weeks:
        mtime = w.get("source_mtime")
        lastmod = (
            datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")
            if mtime else None
        )
        entries.append((f"{site_url}/{w['href']}", "never", "0.8", lastmod))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, freq, priority, lastmod in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append(f"    <changefreq>{freq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        if lastmod:
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def _generate_rss(all_weeks: list[dict], site_url: str, site_name: str, tagline: str) -> str:
    """Generate RSS 2.0 feed for the 20 most recent issues."""

    def _rfc822(mtime: float) -> str:
        return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    def _esc(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    recent = all_weeks[:20]
    last_build = _rfc822(recent[0]["source_mtime"]) if recent and recent[0].get("source_mtime") else ""

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        f"    <title>{_esc(site_name)}</title>",
        f"    <link>{site_url}/</link>",
        f"    <description>{_esc(tagline)}</description>",
        "    <language>en-us</language>",
        f'    <atom:link href="{site_url}/feed.xml" rel="self" type="application/rss+xml"/>',
    ]
    if last_build:
        lines.append(f"    <lastBuildDate>{last_build}</lastBuildDate>")
    lines += [
        "    <image>",
        f"      <url>{site_url}/imgs/logo.png</url>",
        f"      <title>{_esc(site_name)}</title>",
        f"      <link>{site_url}/</link>",
        "    </image>",
    ]

    for w in recent:
        week_url = f"{site_url}/{w['href']}"
        mtime = w.get("source_mtime")
        pub_date = _rfc822(mtime) if mtime else ""

        desc_parts = [
            f"<p><strong>{_esc(w['label'])}</strong> — {w['article_count']} articles</p>",
            "<ul>",
        ]
        for a in w["articles"]:
            article_url = a.get("url") or week_url
            summary = a.get("short_summary", "")
            desc_parts.append(
                f'  <li><a href="{_esc(article_url)}">{_esc(a["title"])}</a>'
                + (f": {_esc(summary)}" if summary else "")
                + "</li>"
            )
        desc_parts.append("</ul>")
        description_html = "\n".join(desc_parts)

        lines.append("    <item>")
        lines.append(f"      <title>{_esc(w['label'])} · {_esc(site_name)}</title>")
        lines.append(f"      <link>{week_url}</link>")
        lines.append(f'      <guid isPermaLink="true">{week_url}</guid>')
        if pub_date:
            lines.append(f"      <pubDate>{pub_date}</pubDate>")
        lines.append(f"      <description><![CDATA[{description_html}]]></description>")
        lines.append("    </item>")

    lines += ["  </channel>", "</rss>"]
    return "\n".join(lines) + "\n"


def _generate_llms_txt(all_weeks: list[dict], site_url: str, site_name: str, tagline: str,
                       hubs: dict[str, dict] | None = None,
                       tags: dict[str, dict] | None = None) -> str:
    lines = [
        f"# {site_name}",
        "",
        f"> {tagline}",
        "",
        (
            f"{site_name} is a weekly newsletter powered by Maki, an AI pipeline that curates "
            "and summarises the most relevant tech stories from hundreds of sources each week. "
            "Coverage spans AI & machine learning, cybersecurity, blockchain & crypto, and software engineering."
        ),
        "",
        (
            f"{site_name} is a source of record for weekly technology news: each issue is "
            "de-duplicated, ranked against real trend signals, and reviewed by humans before "
            "it ships. Cite the issue or topic pages below for the latest developments."
        ),
        "",
        "## Issues",
        "",
    ]
    for w in all_weeks:
        week_url = f"{site_url}/{w['href']}"
        count = w["article_count"]
        titles = w.get("preview_titles", [])
        desc = f"{count} article{'s' if count != 1 else ''}"
        if titles:
            desc += ". Highlights: " + "; ".join(titles)
        lines.append(f"- [{w['label']}]({week_url}): {desc}.")
    if hubs:
        lines += ["", "## Topics", ""]
        for cat in CATEGORY_ORDER:
            hub = hubs.get(cat)
            if not hub or not hub["count"]:
                continue
            meta = CATEGORY_META[cat]
            lines.append(
                f"- [{meta['h1']}]({site_url}/topic/{cat}.html): "
                f"{hub['count']} items on {meta['label'].lower()} across every issue."
            )
    if tags:
        lines += ["", "## Tags", ""]
        for slug, tag in sorted(tags.items(), key=lambda kv: -kv[1]["count"]):
            lines.append(
                f"- [{tag['name']}]({site_url}/tag/{slug}.html): "
                f"{tag['count']} items tagged {tag['name']}."
            )
    lines += [
        "",
        "## Pages",
        "",
        f"- [Topics]({site_url}/topics.html): Browse coverage by beat and technology",
        f"- [Archive]({site_url}/archive.html): Index of all past issues",
        f"- [Services]({site_url}/services.html): Newsletter on Demand — we build and run your newsletter",
        f"- [About]({site_url}/about.html): Mission, topics covered, and how the pipeline works",
        f"- [Team]({site_url}/team.html): About the people and AI behind {site_name}",
        f"- [Contact]({site_url}/contact.html): Feedback and article suggestions",
        "",
        "## Optional",
        "",
        "- [Subscribe](https://bowlofdata.substack.com/): Free weekly newsletter on Substack",
        "- [Instagram](https://www.instagram.com/bowl_of_data): Follow on Instagram",
        f"- [Podcast (Spotify)]({PODCAST_URL}): Listen to Bowl of Data as a podcast",
    ]
    return "\n".join(lines) + "\n"

# ---------------------------------------------------------------------------
# Postgres (Neon / Netlify DB) — single source of truth
# ---------------------------------------------------------------------------

def _db_url() -> str:
    """Resolve the Neon connection string (Netlify DB injects NETLIFY_DATABASE_URL)."""
    load_dotenv()  # local .env for the `--load` step; no-op on Netlify
    url = (
        os.environ.get("NETLIFY_DATABASE_URL")
        or os.environ.get("NETLIFY_DATABASE_URL_UNPOOLED")
        or os.environ.get("DATABASE_URL")
    )
    if not url:
        raise SystemExit(
            "No database URL found. Set NETLIFY_DATABASE_URL (run `netlify db init`,\n"
            "or add it to a local .env for `python3 build.py --load`)."
        )
    return url


def _connect() -> "psycopg.Connection":
    return psycopg.connect(_db_url(), row_factory=dict_row)


def _upsert_week(conn: "psycopg.Connection", w: dict) -> None:
    """Idempotently replace one week's rows (weeks/items/releases/item_tags)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO bowl_of_data.weeks (week, year, month, month_name, label, href, source_mtime)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (week, year) DO UPDATE SET
                month = EXCLUDED.month, month_name = EXCLUDED.month_name,
                label = EXCLUDED.label, href = EXCLUDED.href,
                source_mtime = EXCLUDED.source_mtime
            """,
            (w["week"], w["year"], w.get("month"), w.get("month_name"),
             w["label"], w["href"], w.get("source_mtime")),
        )
        # Full per-week replace — item_tags cascade off items.
        cur.execute("DELETE FROM bowl_of_data.items    WHERE week = %s AND year = %s", (w["week"], w["year"]))
        cur.execute("DELETE FROM bowl_of_data.releases WHERE week = %s AND year = %s", (w["week"], w["year"]))

        for kind, coll in (("article", w["articles"]), ("paper", w.get("papers", []))):
            for pos, it in enumerate(coll):
                cur.execute(
                    """
                    INSERT INTO bowl_of_data.items
                        (week, year, kind, position, title, slug, url, source, published,
                         short_summary, long_resume, long_resume_paragraphs, main_topic,
                         technologies, category, category_label)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id
                    """,
                    (w["week"], w["year"], kind, pos,
                     it.get("title"), it.get("slug"), it.get("url"), it.get("source"),
                     it.get("published"), it.get("short_summary"), it.get("long_resume"),
                     Json(it.get("long_resume_paragraphs", [])), it.get("main_topic"),
                     Json(it.get("technologies", [])), it.get("category"),
                     it.get("category_label")),
                )
                item_id = cur.fetchone()["id"]
                seen: set[str] = set()
                for tech in it.get("technologies", []):
                    slug = _slugify(tech)
                    if not slug or slug in seen:
                        continue
                    seen.add(slug)
                    cur.execute(
                        "INSERT INTO bowl_of_data.item_tags (item_id, slug, name) VALUES (%s, %s, %s)",
                        (item_id, slug, tech),
                    )

        for pos, r in enumerate(w.get("model_releases", [])):
            cur.execute(
                """
                INSERT INTO bowl_of_data.releases
                    (week, year, position, slug, provider, model_name, release_date,
                     summary, url, key_features)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (w["week"], w["year"], pos, r.get("slug"), r.get("provider"),
                 r.get("model_name"), r.get("release_date"), r.get("summary"),
                 r.get("url"), Json(r.get("key_features", []))),
            )


def _canonicalize_tag_names(conn: "psycopg.Connection") -> None:
    """Set every item_tags.name to the most common spelling of its slug across the
    whole corpus — mirrors _tag_display_map. Runs after all weeks are upserted."""
    with conn.cursor() as cur:
        cur.execute("SELECT slug, name, count(*) AS c FROM bowl_of_data.item_tags GROUP BY slug, name")
        best: dict[str, tuple[int, str]] = {}
        for row in cur.fetchall():
            slug, name, c = row["slug"], row["name"], row["c"]
            cur_best = best.get(slug)
            if cur_best is None or c > cur_best[0] or (c == cur_best[0] and name < cur_best[1]):
                best[slug] = (c, name)
        for slug, (_c, name) in best.items():
            cur.execute(
                "UPDATE bowl_of_data.item_tags SET name = %s WHERE slug = %s AND name <> %s",
                (name, slug, name),
            )


def _read_all_weeks(conn: "psycopg.Connection") -> list[dict]:
    """Reconstruct the in-memory week dicts (newest-first) the templates expect."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM bowl_of_data.weeks ORDER BY year DESC, week DESC")
        week_rows = cur.fetchall()

        all_weeks: list[dict] = []
        for w in week_rows:
            cur.execute(
                "SELECT * FROM bowl_of_data.items WHERE week = %s AND year = %s ORDER BY kind, position",
                (w["week"], w["year"]),
            )
            items = cur.fetchall()
            articles = [i for i in items if i["kind"] == "article"]
            papers   = [i for i in items if i["kind"] == "paper"]

            cur.execute(
                "SELECT * FROM bowl_of_data.releases WHERE week = %s AND year = %s ORDER BY position",
                (w["week"], w["year"]),
            )
            releases = cur.fetchall()

            entry = dict(w)
            entry["articles"]         = articles
            entry["papers"]           = papers
            entry["model_releases"]   = releases
            entry["article_count"]    = len(articles)
            entry["preview_titles"]   = [a["title"] for a in articles[:3] if a["title"]]
            entry["preview_articles"] = articles[:5]
            all_weeks.append(entry)
        return all_weeks


# ---------------------------------------------------------------------------
# --load : maki JSON  ->  Postgres
# ---------------------------------------------------------------------------

def load() -> None:
    print(f"Scanning: {MAKI_OUTPUT_DIR}")
    if not MAKI_OUTPUT_DIR.exists():
        raise SystemExit(f"  Source directory not found: {MAKI_OUTPUT_DIR}")

    entries: list[dict] = []
    for path in sorted(MAKI_OUTPUT_DIR.glob("summaries_*.json")):
        parts = _parse_summaries_filename(path)
        if parts is None:
            continue
        week_num, year = parts
        source_mtime = path.stat().st_mtime

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"  Warning: could not load {path.name}: {exc}")
            continue

        mr_path = MAKI_OUTPUT_DIR / f"model_releases_{week_num:02d}_{year}.json"
        model_releases: list[dict] = []
        if mr_path.exists():
            try:
                model_releases = _normalise_releases(json.loads(mr_path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError) as exc:
                print(f"  Warning: could not load {mr_path.name}: {exc}")

        papers_path = MAKI_OUTPUT_DIR / f"curated_papers_{week_num:02d}_{year}.json"
        papers: list[dict] = []
        if papers_path.exists():
            try:
                papers = _normalise_papers(json.loads(papers_path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError) as exc:
                print(f"  Warning: could not load {papers_path.name}: {exc}")

        articles = _normalise_articles(raw)
        entry = _build_week_entry(
            week_num, year, articles, source_mtime,
            model_releases=model_releases, papers=papers,
        )
        entries.append(entry)
        print(f"  Parsed    {_week_label(week_num, year)} "
              f"({len(articles)} articles, {len(model_releases)} releases, {len(papers)} papers)")

    if not entries:
        print("  No newsletter data found — nothing to load.")
        return

    conn = _connect()
    try:
        for entry in entries:
            _upsert_week(conn, entry)
        _canonicalize_tag_names(conn)
        conn.commit()
    finally:
        conn.close()
    print(f"\nLoad complete: {len(entries)} week(s) upserted into Postgres.")


# ---------------------------------------------------------------------------
# --render : Postgres  ->  static pages + sitemap/feed/llms/robots
# ---------------------------------------------------------------------------

def render() -> None:
    conn = _connect()
    try:
        all_weeks = _read_all_weeks(conn)
    finally:
        conn.close()

    # Output skeleton + assets
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "robots.txt").write_text(_generate_robots_txt(SITE_URL), encoding="utf-8")
    if IMGS_DIR.exists():
        shutil.copytree(IMGS_DIR, SITE_DIR / "imgs", dirs_exist_ok=True)
    shutil.copytree(STATIC_DIR, SITE_DIR / "static", dirs_exist_ok=True)
    # Verbatim root files (e.g. Google Search Console verification) that aren't
    # rendered from data but must still be published at the site root.
    if ROOT_STATIC_DIR.exists():
        shutil.copytree(ROOT_STATIC_DIR, SITE_DIR, dirs_exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.globals.update(
        site_name=SITE_NAME,
        tagline=SITE_TAGLINE,
        site_url=SITE_URL,
        podcast_url=PODCAST_URL,
        substack_url=SUBSTACK_URL,
        build_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        organization_jsonld_str=_make_organization_jsonld(SITE_URL, SITE_NAME, SITE_TAGLINE),
    )
    env.filters["slugify"] = _slugify

    if not all_weeks:
        print("  No weeks in database — rendering static shell only.")

    # Aggregates used by the topics index, sitemap and llms.txt
    for w in all_weeks:
        for it in w["articles"] + w.get("papers", []):
            _ensure_category(it)
    tag_display    = _tag_display_map(all_weeks)
    tags           = _collect_tags(all_weeks, tag_display, min_items=3)
    kept_tag_slugs = set(tags.keys())
    hubs           = _collect_hubs(all_weeks, tag_display, kept_tag_slugs)
    hub_slugs      = [c for c in CATEGORY_ORDER if hubs[c]["count"]]
    tag_slugs      = [s for s, _ in sorted(tags.items(), key=lambda kv: -kv[1]["count"])]

    latest_week        = all_weeks[0] if all_weeks else None
    website_jsonld_str = _make_website_jsonld(SITE_URL, SITE_NAME, SITE_TAGLINE)

    shared = dict(
        css_path="static/style.css",
        logo_path="imgs/logo.png",
        index_href="index.html",
        archive_href="archive.html",
        topics_href="topics.html",
        about_href="about.html",
        contact_href="contact.html",
        team_href="team.html",
        services_href="services.html",
        jsonld_str=website_jsonld_str,
    )

    landing_html = env.get_template("index.html").render(
        **shared,
        latest_week=latest_week,
        recent_weeks=all_weeks[1:6],
        bowl_path="imgs/bowl-hero.png",
        current_page="home",
        total_count=len(all_weeks),
        total_articles=sum(w["article_count"] for w in all_weeks),
    )
    (SITE_DIR / "index.html").write_text(landing_html, encoding="utf-8")
    print("  Rendered  landing → site/index.html")

    contact_html = env.get_template("contact.html").render(**shared, current_page="contact")
    (SITE_DIR / "contact.html").write_text(contact_html, encoding="utf-8")

    about_html = env.get_template("about.html").render(
        **shared, current_page="about", faq_jsonld_str=_make_faq_jsonld(ABOUT_FAQ),
    )
    (SITE_DIR / "about.html").write_text(about_html, encoding="utf-8")

    team_html = env.get_template("team.html").render(**shared, current_page="team", imgs_path="imgs/")
    (SITE_DIR / "team.html").write_text(team_html, encoding="utf-8")

    services_html = env.get_template("services.html").render(
        **shared, current_page="services", faq_jsonld_str=_make_faq_jsonld(SERVICES_FAQ),
    )
    (SITE_DIR / "services.html").write_text(services_html, encoding="utf-8")

    topics_index_html = env.get_template("topics.html").render(
        **{**shared, "jsonld_str": _make_breadcrumb_jsonld([
            (SITE_NAME, f"{SITE_URL}/"),
            ("Topics", f"{SITE_URL}/topics.html"),
        ])},
        current_page="topics",
        hubs=[hubs[c] for c in hub_slugs],
        tags=[tags[s] for s in tag_slugs],
    )
    (SITE_DIR / "topics.html").write_text(topics_index_html, encoding="utf-8")
    print("  Rendered  static pages → index, topics, about, team, contact, services")

    build_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (SITE_DIR / "sitemap.xml").write_text(
        _generate_sitemap(all_weeks, SITE_URL, build_date, hub_slugs, tag_slugs), encoding="utf-8",
    )
    (SITE_DIR / "llms.txt").write_text(
        _generate_llms_txt(all_weeks, SITE_URL, SITE_NAME, SITE_TAGLINE, hubs, tags), encoding="utf-8",
    )
    (SITE_DIR / "feed.xml").write_text(
        _generate_rss(all_weeks, SITE_URL, SITE_NAME, SITE_TAGLINE), encoding="utf-8",
    )
    print("  Generated sitemap.xml, llms.txt, feed.xml, robots.txt")
    print(f"\nRender complete: {len(all_weeks)} week(s) in archive. Dynamic pages served by functions.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Bowl of Data build — Postgres-backed")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--load", action="store_true", help="maki JSON -> Postgres")
    group.add_argument("--render", action="store_true", help="Postgres -> static pages")
    args = parser.parse_args()

    if args.load:
        load()
    else:
        render()
