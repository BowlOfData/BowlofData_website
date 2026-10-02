#!/usr/bin/env python3
"""Reorder archived issues to lead with the stories their Substack post led with.

build.py orders an issue by the pipeline's channel_selection_WW_YYYY.json, but
that file rotates out of the maki output directory with everything else, so
every week cached in weeks_manifest.json before the ordering fix kept the
unranked pool order (week 38 opened with a quantum-physics item). The ranking
still exists in public: each weekly Substack post lists its stories as bold
headlines in the order the newsletter ranked them.

This reads those posts, matches each headline to the issue's articles by title,
moves the matched stories to the front in post order, and leaves everything
else in its existing relative order. Anchors are slugs, not positions, so no
link into an issue changes.

    python3 scripts/backfill_story_order.py            # dry run: print the matches
    python3 scripts/backfill_story_order.py --apply    # write weeks_manifest.json

Then re-render: FORCE_REBUILD=1 python3 build.py
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build  # noqa: E402

SUBSTACK = "https://bowlofdata.substack.com"
WEEK_TITLE = re.compile(r"Week\s+(\d{1,2}),\s*(\d{4})")
STRONG = re.compile(r"<strong[^>]*>(.*?)</strong>", re.S)
# A headline this close to an article title is the same story. Substack
# headlines are the stored titles, give or take punctuation and shortening:
# across weeks 26-38 the correct matches bottomed out at 0.69 ("CISA Warns of
# MLflow Vulnerability" vs its full title) and no wrong pairing scored above
# 0.6, so the bar sits between them.
MIN_SIMILARITY = 0.65


def _get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "bowlofdata-backfill/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", html.unescape(text).lower()).strip()


def _similarity(a: str, b: str) -> float:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return 0.0
    if a.startswith(b) or b.startswith(a):
        return 1.0 if min(len(a), len(b)) >= 25 else 0.0
    return SequenceMatcher(None, a, b).ratio()


def weekly_posts() -> dict[tuple[int, int], str]:
    """(week, year) -> post slug, for every weekly issue post."""
    posts = _get_json(f"{SUBSTACK}/api/v1/archive?sort=new&limit=50")
    found: dict[tuple[int, int], str] = {}
    for post in posts:
        match = WEEK_TITLE.search(post.get("title") or "")
        if match:
            found.setdefault((int(match.group(1)), int(match.group(2))), post["slug"])
    return found


def ranked_titles(slug: str) -> list[str]:
    body = _get_json(f"{SUBSTACK}/api/v1/posts/{slug}").get("body_html") or ""
    return [re.sub(r"<[^>]+>", "", m).strip() for m in STRONG.findall(body)]


def lead_order(articles: list[dict], headlines: list[str]) -> tuple[list[dict], list[str]]:
    """Articles reordered by headline position, plus the headlines that matched."""
    rank: dict[int, int] = {}
    matched: list[str] = []
    for pos, headline in enumerate(headlines):
        best_i, best_score = None, 0.0
        for i, art in enumerate(articles):
            if i in rank:
                continue
            score = _similarity(headline, art.get("title", ""))
            if score > best_score:
                best_i, best_score = i, score
        if best_i is not None and best_score >= MIN_SIMILARITY:
            rank[best_i] = pos
            matched.append(headline)
    order = sorted(range(len(articles)), key=lambda i: (rank.get(i, len(headlines)), i))
    return [articles[i] for i in order], matched


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="write weeks_manifest.json")
    args = parser.parse_args()

    manifest = build._load_manifest()
    posts = weekly_posts()
    changed = 0

    for key in sorted(manifest):
        entry = manifest[key]
        if entry.get("selection_mtime"):
            print(f"  {entry['label']}: ordered by channel_selection, left alone")
            continue
        slug = posts.get(key)
        if not slug:
            print(f"  {entry['label']}: no Substack post, left alone")
            continue
        articles, matched = lead_order(entry["articles"], ranked_titles(slug))
        before = [a["title"] for a in entry["articles"][:3]]
        after = [a["title"] for a in articles[:3]]
        print(f"  {entry['label']}: matched {len(matched)} headline(s) from {slug}")
        for title in after:
            print(f"      {title[:90]}")
        if after == before:
            continue
        changed += 1
        manifest[key] = build._build_week_entry(
            entry["week"], entry["year"], articles, entry.get("source_mtime", 0),
            model_releases=entry.get("model_releases", []),
            model_releases_mtime=entry.get("model_releases_mtime", 0),
            papers=entry.get("papers", []),
            papers_mtime=entry.get("papers_mtime", 0),
            selection_mtime=entry.get("selection_mtime", 0),
        )

    if args.apply and changed:
        build._save_manifest(manifest)
        print(f"\nReordered {changed} issue(s). Now run: FORCE_REBUILD=1 python3 build.py")
    else:
        print(f"\n{changed} issue(s) would change. Re-run with --apply to write the manifest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
