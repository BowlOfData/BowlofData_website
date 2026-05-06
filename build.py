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
        str(HERE.parent / "maki" / "maki_newsletter" / "output"),
    )
)

FORCE_REBUILD = os.environ.get("FORCE_REBUILD", "").strip() not in ("", "0")

SITE_NAME    = "Bowl of Data"
SITE_TAGLINE = "A weekly digest of the most relevant tech stories"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_summaries_filename(path: Path) -> tuple[int, int] | None:
    """Return (week_num, year) from `summaries_WW_YYYY.json`, or None."""
    match = re.fullmatch(r"summaries_(\d{2})_(\d{4})\.json", path.name)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _week_label(week: int, year: int) -> str:
    return f"Week {week:02d} · {year}"


def _week_href(week: int, year: int) -> str:
    return f"week/{week:02d}_{year}.html"


def _normalise_articles(raw_articles: list[dict]) -> list[dict]:
    """Normalise raw article dicts from a pipeline summaries JSON."""
    result = []
    for a in raw_articles:
        resume_raw = (a.get("long_resume") or "").strip()
        resume_paragraphs = [p.strip() for p in resume_raw.split("\n\n") if p.strip()] if resume_raw else []
        result.append({
            "title":                  (a.get("title") or "").strip(),
            "url":                    (a.get("url") or "").strip(),
            "source":                 (a.get("source") or "").strip(),
            "published":              (a.get("published") or "").strip(),
            "short_summary":          (a.get("short_summary") or "").strip(),
            "long_resume":            resume_raw,
            "long_resume_paragraphs": resume_paragraphs,
            "main_topic":             (a.get("main_topic") or "").strip(),
            "score":                  int(a.get("quality_score") or 0),
            "technologies":           [t.strip() for t in (a.get("technologies") or []) if t and t.strip()],
        })
    return result


def _build_week_entry(week: int, year: int, articles: list[dict], source_mtime: float) -> dict:
    """Build a complete week entry for storage in the manifest."""
    return {
        "week":             week,
        "year":             year,
        "label":            _week_label(week, year),
        "href":             _week_href(week, year),
        "articles":         articles,
        "article_count":    len(articles),
        "preview_titles":   [a["title"] for a in articles[:3] if a["title"]],
        "preview_articles": articles[:5],
        "source_mtime":     source_mtime,
    }

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

    # Ensure site output skeleton exists (safe on repeated runs)
    (SITE_DIR / "week").mkdir(parents=True, exist_ok=True)

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
        build_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    )

    # ------------------------------------------------------------------
    # Phase 1: load manifest and reconcile with current source files
    # ------------------------------------------------------------------
    manifest: dict[tuple[int, int], dict] = {} if FORCE_REBUILD else _load_manifest()
    needs_rebuild: set[tuple[int, int]] = set()

    for path in sorted(MAKI_OUTPUT_DIR.glob("summaries_*.json")):
        parts = _parse_summaries_filename(path)
        if parts is None:
            continue
        week_num, year = parts
        key = (week_num, year)
        source_mtime = path.stat().st_mtime
        html_exists = (SITE_DIR / _week_href(week_num, year)).exists()

        existing = manifest.get(key)
        if (
            not FORCE_REBUILD
            and existing is not None
            and source_mtime <= existing.get("source_mtime", 0)
            and html_exists
        ):
            print(f"  Skipping  {_week_label(week_num, year)} — up to date")
            continue

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"  Warning: could not load {path.name}: {exc}")
            continue

        articles = _normalise_articles(raw)
        manifest[key] = _build_week_entry(week_num, year, articles, source_mtime)
        needs_rebuild.add(key)
        verb = "forced" if FORCE_REBUILD else ("new" if existing is None else "updated")
        print(f"  Queued    {_week_label(week_num, year)} ({verb}, {len(articles)} articles)")

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
            all_weeks=all_weeks,
            prev_week=prev_week,
            next_week=next_week,
            css_path="../static/style.css",
            logo_path="../imgs/logo.png",
            index_href="../index.html",
            archive_href="../archive.html",
            contact_href="../contact.html",
        )
        out_path.write_text(html, encoding="utf-8")
        print(f"  Rendered  {w['label']} ({w['article_count']} articles) → {out_path.relative_to(HERE)}")
        rendered_count += 1

    # ------------------------------------------------------------------
    # Phase 4: always regenerate the landing page and archive index
    # ------------------------------------------------------------------
    latest_week = all_weeks[0] if all_weeks else None

    shared = dict(
        css_path="static/style.css",
        logo_path="imgs/logo.png",
        index_href="index.html",
        archive_href="archive.html",
        contact_href="contact.html",
    )

    landing_html = env.get_template("index.html").render(
        **shared,
        latest_week=latest_week,
        bowl_path="imgs/bowl.png",
    )
    (SITE_DIR / "index.html").write_text(landing_html, encoding="utf-8")
    print(f"  Rendered  landing → site/index.html")

    archive_html = env.get_template("archive.html").render(
        **shared,
        weeks=all_weeks,
    )
    (SITE_DIR / "archive.html").write_text(archive_html, encoding="utf-8")
    print(f"  Rendered  archive → site/archive.html")

    contact_html = env.get_template("contact.html").render(**shared)
    (SITE_DIR / "contact.html").write_text(contact_html, encoding="utf-8")
    print(f"  Rendered  contact → site/contact.html")

    # ------------------------------------------------------------------
    # Phase 5: persist the manifest
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
