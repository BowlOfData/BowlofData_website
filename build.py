"""
BowlofData Website Builder — incremental

Reads summaries_WW_YYYY.json files from the maki newsletter output directory,
renders them into static HTML pages using Jinja2, and writes a self-contained
site into the `site/` directory.

Incremental behaviour
---------------------
- A manifest file (`weeks_manifest.json` at the repo root) tracks every week
  that has ever been built, including its full normalised article data and the
  mtime of the source file at the time it was last rendered.
- On each run only weeks whose source JSON is new or has changed (mtime newer
  than the manifest entry) are re-rendered, plus their immediate neighbours so
  that prev/next links stay accurate.
- Weeks whose source JSON has been removed from the maki output are kept in the
  manifest and their HTML is left untouched — the archive index always reflects
  every issue ever published.

Usage:
    python3 build.py

Override the maki output path:
    MAKI_OUTPUT_DIR=/path/to/output python3 build.py

Force a full rebuild (ignores the manifest):
    FORCE_REBUILD=1 python3 build.py
"""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HERE          = Path(__file__).parent
TEMPLATES_DIR = HERE / "templates"
STATIC_DIR    = HERE / "static"
IMGS_DIR      = HERE / "imgs"
SITE_DIR      = HERE / "site"
MANIFEST_PATH = HERE / "weeks_manifest.json"   # outside site/ so it survives gitignore

MAKI_OUTPUT_DIR = Path(
    os.environ.get(
        "MAKI_OUTPUT_DIR",
        str(HERE.parent / "maki_newsletter" / "maki_newsletter" / "output"),
    )
)

FORCE_REBUILD = os.environ.get("FORCE_REBUILD", "").strip() not in ("", "0")

SITE_NAME    = "Bowl of Data"
SITE_TAGLINE = "A weekly digest of the most relevant tech stories"
SITE_URL     = "https://bowlofdata.netlify.app"

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


def _normalise_articles(raw_articles: list[dict]) -> list[dict]:
    """Normalise raw article dicts from a pipeline summaries JSON."""
    result = []
    for a in raw_articles:
        resume_raw = (a.get("long_resume") or "").strip()
        resume_paragraphs = [p.strip() for p in resume_raw.split("\n\n") if p.strip()] if resume_raw else []
        title = (a.get("title") or "").strip()
        result.append({
            "title":                  title,
            "slug":                   _slugify(title),
            "url":                    (a.get("url") or "").strip(),
            "source":                 (a.get("source") or "").strip(),
            "published":              (a.get("published") or "").strip(),
            "short_summary":          (a.get("short_summary") or "").strip(),
            "long_resume":            resume_raw,
            "long_resume_paragraphs": resume_paragraphs,
            "main_topic":             (a.get("main_topic") or "").strip(),
            "technologies":           [t.strip() for t in (a.get("technologies") or []) if t and t.strip()],
        })
    return result


def _build_week_entry(
    week: int,
    year: int,
    articles: list[dict],
    source_mtime: float,
    model_releases: list[dict] | None = None,
    model_releases_mtime: float = 0,
) -> dict:
    """Build a complete week entry for storage in the manifest."""
    return {
        "week":                  week,
        "year":                  year,
        "label":                 _week_label(week, year),
        "href":                  _week_href(week, year),
        "articles":              articles,
        "article_count":         len(articles),
        "preview_titles":        [a["title"] for a in articles[:3] if a["title"]],
        "preview_articles":      articles[:5],
        "source_mtime":          source_mtime,
        "model_releases":        model_releases or [],
        "model_releases_mtime":  model_releases_mtime,
    }

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


def _make_week_jsonld(w: dict, site_url: str, site_name: str) -> str:
    count = w["article_count"]
    week_url = f"{site_url}/{w['href']}"
    items: list[dict[str, Any]] = []
    for i, a in enumerate(w["articles"], 1):
        entry: dict[str, Any] = {
            "@type": "ListItem",
            "position": i,
            "item": {
                "@type": "NewsArticle",
                "headline": a["title"],
                "url": a["url"] or week_url,
            },
        }
        if a.get("short_summary"):
            entry["item"]["description"] = a["short_summary"]
        if a.get("published"):
            entry["item"]["datePublished"] = a["published"]
        items.append(entry)
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": f"{w['label']} · {site_name}",
        "description": (
            f"{count} article{'s' if count != 1 else ''} curated this week "
            "covering AI, cybersecurity, blockchain and engineering."
        ),
        "url": week_url,
        "publisher": {"@type": "Organization", "name": site_name, "url": site_url},
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": count,
            "itemListElement": items,
        },
    }, ensure_ascii=False)


def _generate_robots_txt(site_url: str) -> str:
    bots = ["GPTBot", "ClaudeBot", "PerplexityBot", "Applebot-Extended", "Googlebot"]
    lines = ["User-agent: *", "Allow: /", ""]
    for bot in bots:
        lines += [f"User-agent: {bot}", "Allow: /", ""]
    lines.append(f"Sitemap: {site_url}/sitemap.xml")
    return "\n".join(lines) + "\n"


def _generate_sitemap(all_weeks: list[dict], site_url: str, build_date: str) -> str:
    entries = [
        (f"{site_url}/",               "weekly",  "1.0", build_date),
        (f"{site_url}/archive.html",   "weekly",  "0.9", build_date),
        (f"{site_url}/about.html",     "monthly", "0.6", None),
        (f"{site_url}/team.html",      "monthly", "0.5", None),
        (f"{site_url}/contact.html",   "monthly", "0.5", None),
    ]
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


def _generate_llms_txt(all_weeks: list[dict], site_url: str, site_name: str, tagline: str) -> str:
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
    lines += [
        "",
        "## Pages",
        "",
        f"- [Archive]({site_url}/archive.html): Index of all past issues",
        f"- [About]({site_url}/about.html): Mission, topics covered, and how the pipeline works",
        f"- [Team]({site_url}/team.html): About the people and AI behind {site_name}",
        f"- [Contact]({site_url}/contact.html): Feedback and article suggestions",
        "",
        "## Optional",
        "",
        "- [Subscribe](https://bowlofdata.substack.com/): Free weekly newsletter on Substack",
        "- [Instagram](https://www.instagram.com/bowl_of_data): Follow on Instagram",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Manifest  (persistent build state)
# ---------------------------------------------------------------------------

def _load_manifest() -> dict[tuple[int, int], dict]:
    """
    Load the weeks manifest from disk.
    Returns a dict keyed by (week, year).
    Returns an empty dict when no manifest exists yet.
    """
    if not MANIFEST_PATH.exists():
        return {}
    try:
        entries = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        return {(e["week"], e["year"]): e for e in entries}
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"  Warning: could not load manifest ({exc}) — treating all weeks as new")
        return {}


def _save_manifest(manifest: dict[tuple[int, int], dict]) -> None:
    """Write the manifest to disk, sorted newest-first."""
    entries = sorted(manifest.values(), key=lambda e: (e["year"], e["week"]), reverse=True)
    MANIFEST_PATH.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build() -> None:
    print(f"Scanning: {MAKI_OUTPUT_DIR}")
    if FORCE_REBUILD:
        print("  FORCE_REBUILD=1 — ignoring manifest, will re-render all weeks")
    if not MAKI_OUTPUT_DIR.exists():
        print(f"  Note: source directory not found — building from manifest only")

    # Ensure site output skeleton exists (safe on repeated runs)
    (SITE_DIR / "week").mkdir(parents=True, exist_ok=True)

    # robots.txt never changes with content — write it unconditionally so it
    # is always present even on a first run with no newsletter data
    (SITE_DIR / "robots.txt").write_text(_generate_robots_txt(SITE_URL), encoding="utf-8")

    # Sync brand assets and static files on every run so edits are picked up
    if IMGS_DIR.exists():
        shutil.copytree(IMGS_DIR, SITE_DIR / "imgs", dirs_exist_ok=True)
    shutil.copytree(STATIC_DIR, SITE_DIR / "static", dirs_exist_ok=True)

    # Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.globals.update(
        site_name=SITE_NAME,
        tagline=SITE_TAGLINE,
        site_url=SITE_URL,
        build_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    )

    # ------------------------------------------------------------------
    # Phase 1: load manifest and reconcile with current source files
    # ------------------------------------------------------------------
    manifest: dict[tuple[int, int], dict] = {} if FORCE_REBUILD else _load_manifest()
    needs_rebuild: set[tuple[int, int]] = set()

    for path in sorted(MAKI_OUTPUT_DIR.glob("summaries_*.json")) if MAKI_OUTPUT_DIR.exists() else []:
        parts = _parse_summaries_filename(path)
        if parts is None:
            continue
        week_num, year = parts
        key = (week_num, year)
        source_mtime = path.stat().st_mtime

        mr_path = MAKI_OUTPUT_DIR / f"model_releases_{week_num:02d}_{year}.json"
        mr_mtime = mr_path.stat().st_mtime if mr_path.exists() else 0

        html_exists = (SITE_DIR / _week_href(week_num, year)).exists()

        existing = manifest.get(key)
        if (
            not FORCE_REBUILD
            and existing is not None
            and source_mtime <= existing.get("source_mtime", 0)
            and mr_mtime <= existing.get("model_releases_mtime", 0)
            and html_exists
        ):
            print(f"  Skipping  {_week_label(week_num, year)} — up to date")
            continue

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"  Warning: could not load {path.name}: {exc}")
            continue

        model_releases: list[dict] = []
        if mr_path.exists():
            try:
                model_releases = _normalise_releases(
                    json.loads(mr_path.read_text(encoding="utf-8"))
                )
            except (OSError, json.JSONDecodeError) as exc:
                print(f"  Warning: could not load {mr_path.name}: {exc}")

        articles = _normalise_articles(raw)
        manifest[key] = _build_week_entry(
            week_num, year, articles, source_mtime,
            model_releases=model_releases,
            model_releases_mtime=mr_mtime,
        )
        needs_rebuild.add(key)
        verb = "forced" if FORCE_REBUILD else ("new" if existing is None else "updated")
        releases_note = f", {len(model_releases)} releases" if model_releases else ""
        print(f"  Queued    {_week_label(week_num, year)} ({verb}, {len(articles)} articles{releases_note})")

    # Queue weeks whose HTML file is absent even though the manifest knows about them
    # (e.g. first run after cloning the repo when site/ was gitignored)
    for key, entry in manifest.items():
        if not (SITE_DIR / entry["href"]).exists():
            needs_rebuild.add(key)
            print(f"  Queued    {entry['label']} (HTML missing, rebuilding from manifest)")

    if not manifest:
        print("  No newsletter data found — nothing to build.")
        return

    # ------------------------------------------------------------------
    # Phase 2: expand render set to include neighbours of changed pages
    # so their prev/next links stay accurate
    # ------------------------------------------------------------------
    all_weeks = sorted(manifest.values(), key=lambda w: (w["year"], w["week"]), reverse=True)
    week_keys  = [(w["week"], w["year"]) for w in all_weeks]

    render_set: set[tuple[int, int]] = set(needs_rebuild)
    for key in list(needs_rebuild):
        idx = week_keys.index(key)
        if idx > 0:
            render_set.add(week_keys[idx - 1])   # newer neighbour
        if idx + 1 < len(week_keys):
            render_set.add(week_keys[idx + 1])   # older neighbour

    # ------------------------------------------------------------------
    # Phase 3: render week pages
    # ------------------------------------------------------------------
    week_tmpl     = env.get_template("week.html")
    rendered_count = 0

    for i, w in enumerate(all_weeks):
        key = (w["week"], w["year"])
        if key not in render_set:
            continue

        next_week = all_weeks[i - 1] if i > 0 else None            # newer issue
        prev_week = all_weeks[i + 1] if i + 1 < len(all_weeks) else None  # older issue

        out_path = SITE_DIR / w["href"]
        html = week_tmpl.render(
            week=w["week"],
            year=w["year"],
            label=w["label"],
            articles=w["articles"],
            model_releases=w.get("model_releases", []),
            all_weeks=all_weeks,
            prev_week=prev_week,
            next_week=next_week,
            css_path="../static/style.css",
            logo_path="../imgs/logo.png",
            index_href="../index.html",
            archive_href="../archive.html",
            about_href="../about.html",
            contact_href="../contact.html",
            team_href="../team.html",
            jsonld_str=_make_week_jsonld(w, SITE_URL, SITE_NAME),
        )
        out_path.write_text(html, encoding="utf-8")
        print(f"  Rendered  {w['label']} ({w['article_count']} articles) → {out_path.relative_to(HERE)}")
        rendered_count += 1

    # ------------------------------------------------------------------
    # Phase 4: always regenerate the landing page and archive index
    # ------------------------------------------------------------------
    latest_week = all_weeks[0] if all_weeks else None
    website_jsonld_str = _make_website_jsonld(SITE_URL, SITE_NAME, SITE_TAGLINE)

    shared = dict(
        css_path="static/style.css",
        logo_path="imgs/logo.png",
        index_href="index.html",
        archive_href="archive.html",
        about_href="about.html",
        contact_href="contact.html",
        team_href="team.html",
        jsonld_str=website_jsonld_str,
    )

    landing_html = env.get_template("index.html").render(
        **shared,
        latest_week=latest_week,
        bowl_path="imgs/bowl.png",
        current_page="home",
    )
    (SITE_DIR / "index.html").write_text(landing_html, encoding="utf-8")
    print(f"  Rendered  landing → site/index.html")

    archive_html = env.get_template("archive.html").render(
        **shared,
        weeks=all_weeks,
        current_page="archive",
    )
    (SITE_DIR / "archive.html").write_text(archive_html, encoding="utf-8")
    print(f"  Rendered  archive → site/archive.html")

    contact_html = env.get_template("contact.html").render(**shared, current_page="contact")
    (SITE_DIR / "contact.html").write_text(contact_html, encoding="utf-8")
    print(f"  Rendered  contact → site/contact.html")

    about_html = env.get_template("about.html").render(**shared, current_page="about")
    (SITE_DIR / "about.html").write_text(about_html, encoding="utf-8")
    print(f"  Rendered  about   → site/about.html")

    team_html = env.get_template("team.html").render(**shared, current_page="team", imgs_path="imgs/")
    (SITE_DIR / "team.html").write_text(team_html, encoding="utf-8")
    print(f"  Rendered  team → site/team.html")

    # ------------------------------------------------------------------
    # Phase 5: generate LLM-friendly and crawler files
    # ------------------------------------------------------------------
    build_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    (SITE_DIR / "sitemap.xml").write_text(
        _generate_sitemap(all_weeks, SITE_URL, build_date), encoding="utf-8"
    )
    print(f"  Generated sitemap → site/sitemap.xml")

    (SITE_DIR / "llms.txt").write_text(
        _generate_llms_txt(all_weeks, SITE_URL, SITE_NAME, SITE_TAGLINE), encoding="utf-8"
    )
    print(f"  Generated llms.txt → site/llms.txt")

    (SITE_DIR / "feed.xml").write_text(
        _generate_rss(all_weeks, SITE_URL, SITE_NAME, SITE_TAGLINE), encoding="utf-8"
    )
    print(f"  Generated feed    → site/feed.xml")

    # ------------------------------------------------------------------
    # Phase 6: persist the manifest
    # ------------------------------------------------------------------
    _save_manifest(manifest)
    print(f"  Saved     manifest → {MANIFEST_PATH.relative_to(HERE)}")

    total   = len(all_weeks)
    skipped = total - len(render_set)
    print(
        f"\nBuild complete: {rendered_count} week(s) rendered, "
        f"{skipped} skipped, {total} total in archive."
    )
    if rendered_count == 0 and skipped == total:
        print("Everything is up to date.")
    else:
        print("Open: site/index.html")


if __name__ == "__main__":
    build()
