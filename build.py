"""
BowlofData Website Builder

Reads summaries_WW_YYYY.json files from the maki newsletter output directory,
renders them into static HTML pages using Jinja2, and writes a self-contained
site into the `site/` directory.

Usage:
    python build.py

Override the maki output path:
    MAKI_OUTPUT_DIR=/path/to/output python build.py
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

HERE = Path(__file__).parent
TEMPLATES_DIR = HERE / "templates"
STATIC_DIR = HERE / "static"
SITE_DIR = HERE / "site"

MAKI_OUTPUT_DIR = Path(
    os.environ.get(
        "MAKI_OUTPUT_DIR",
        str(HERE.parent / "maki" / "maki_newsletter" / "output"),
    )
)

IMGS_DIR = HERE / "imgs"

SITE_NAME = "Bowl of Data"
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


def _load_weeks() -> list[dict[str, Any]]:
    """
    Scan MAKI_OUTPUT_DIR for summaries_*.json files and return a list of
    week dicts sorted newest-first.
    """
    weeks = []
    for path in sorted(MAKI_OUTPUT_DIR.glob("summaries_*.json")):
        parts = _parse_summaries_filename(path)
        if parts is None:
            continue
        week_num, year = parts
        try:
            articles = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"  Warning: could not load {path.name}: {exc}")
            continue

        # Normalise each article dict
        normalised = []
        for a in articles:
            resume_raw = (a.get("long_resume") or "").strip()
            resume_paragraphs = [p.strip() for p in resume_raw.split("\n\n") if p.strip()] if resume_raw else []
            normalised.append({
                "title":                (a.get("title") or "").strip(),
                "url":                  (a.get("url") or "").strip(),
                "source":               (a.get("source") or "").strip(),
                "published":            (a.get("published") or "").strip(),
                "short_summary":        (a.get("short_summary") or "").strip(),
                "long_resume":          resume_raw,
                "long_resume_paragraphs": resume_paragraphs,
                "main_topic":           (a.get("main_topic") or "").strip(),
                "score":                int(a.get("quality_score") or 0),
                "technologies":         [t.strip() for t in (a.get("technologies") or []) if t and t.strip()],
            })

        weeks.append({
            "week":           week_num,
            "year":           year,
            "label":          _week_label(week_num, year),
            "href":           _week_href(week_num, year),
            "articles":       normalised,
            "article_count":  len(normalised),
            "preview_titles": [a["title"] for a in normalised[:3] if a["title"]],
            "preview_articles": normalised[:5],
        })

    # Newest week first
    weeks.sort(key=lambda w: (w["year"], w["week"]), reverse=True)
    return weeks


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build() -> None:
    print(f"Scanning: {MAKI_OUTPUT_DIR}")
    weeks = _load_weeks()
    print(f"Found {len(weeks)} summaries file(s)")

    # Wipe and recreate the output directory
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    (SITE_DIR / "week").mkdir(parents=True)

    # Copy imgs (logo, etc.)
    if IMGS_DIR.exists():
        shutil.copytree(IMGS_DIR, SITE_DIR / "imgs")

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

    # Render each week page
    # weeks is newest-first: index 0 = latest, index -1 = oldest
    # "next" = newer issue (lower index), "prev" = older issue (higher index)
    week_tmpl = env.get_template("week.html")
    for i, w in enumerate(weeks):
        out_path = SITE_DIR / w["href"]
        next_week = weeks[i - 1] if i > 0 else None
        prev_week = weeks[i + 1] if i + 1 < len(weeks) else None
        html = week_tmpl.render(
            week=w["week"],
            year=w["year"],
            label=w["label"],
            articles=w["articles"],
            all_weeks=weeks,
            prev_week=prev_week,
            next_week=next_week,
            css_path="../static/style.css",
            logo_path="../imgs/logo.png",
            index_href="../index.html",
        )
        out_path.write_text(html, encoding="utf-8")
        print(f"  Rendered {w['label']} ({w['article_count']} articles) → {out_path.relative_to(HERE)}")

    # Render index
    index_html = env.get_template("index.html").render(
        weeks=weeks,
        css_path="static/style.css",
        logo_path="imgs/logo.png",
        index_href="index.html",
    )
    (SITE_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print(f"  Rendered index → site/index.html")

    # Copy static assets
    site_static = SITE_DIR / "static"
    shutil.copytree(STATIC_DIR, site_static)
    print(f"  Copied static assets → site/static/")

    print(f"\nBuild complete. Open: site/index.html")


if __name__ == "__main__":
    build()
