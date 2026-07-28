#!/usr/bin/env python3
"""Seed the Altervista mirror with every historical issue from the manifest.

The maki output directory only keeps recent weeks, but the mirror needs the
whole archive — so this one-shot reads weeks_manifest.json (the same source
build.py renders bowlofdata.net from) and pushes each week into the WordPress
content model:

    weeks     -> bod_issue      slug "30_2026"
    items     -> bod_story      post_parent = issue, meta bod_kind article|paper
    releases  -> bod_release    post_parent = issue
    category  -> bod_beat term
    tags      -> bod_tech term

Categories come straight from the manifest, so historical issues keep exactly
the beat they show on bowlofdata.net rather than being re-classified.

Re-running replaces a week's stories and releases, so it is safe to interrupt
and resume. Ongoing weekly publishing is maki_newsletter/wp_sync.py.

    python3 scripts/wp_backfill.py --dry-run
    python3 scripts/wp_backfill.py --limit 1        # one newest week, to check
    python3 scripts/wp_backfill.py                  # everything
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import build  # noqa: E402  (shared slug/label helpers)
from wp_client import WPClient, WPError  # noqa: E402


class TermCache:
    """Look up (and create) taxonomy terms once per run."""

    def __init__(self, wp: WPClient, taxonomy: str):
        self.wp = wp
        self.taxonomy = taxonomy
        self._by_slug: dict[str, int] = {}

    def prime(self) -> None:
        for term in self.wp.paginate(f"/{self.taxonomy}"):
            self._by_slug[term["slug"]] = term["id"]

    def id_for(self, name: str, slug: str) -> int | None:
        if slug in self._by_slug:
            return self._by_slug[slug]
        try:
            created = self.wp.post(f"/{self.taxonomy}", {"name": name, "slug": slug})
        except WPError as exc:
            # A concurrent create (or an existing term REST did not list) comes
            # back as term_exists with the id attached.
            data = exc.body.get("data") if isinstance(exc.body, dict) else None
            existing = data.get("term_id") if isinstance(data, dict) else None
            if not existing:
                print(f"      ! term {self.taxonomy}/{slug}: {exc}")
                return None
            created = {"id": existing}
        term_id = created.get("id")
        if term_id:
            self._by_slug[slug] = term_id
        return term_id


def as_list(value) -> list:
    """jsonb columns come back as lists already; tolerate strings just in case."""
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def push_week(
    wp: WPClient,
    week: dict,
    beats: TermCache,
    techs: TermCache,
) -> None:
    """Create or update one issue and replace all of its children."""
    wk = int(week["week"])
    yr = int(week["year"])
    slug = f"{wk:02d}_{yr}"
    label = week.get("label") or build._week_label(wk, yr)
    # Weeks predating a pipeline feature simply omit the key — the manifest has
    # no "papers" before 2026-W26 — so read defensively rather than by index.
    articles = week.get("articles") or []
    papers = week.get("papers") or []
    releases = week.get("model_releases") or []

    print(f"  {label}: {len(articles)} articles, {len(papers)} papers, {len(releases)} releases")

    issue_meta = {
        "bod_week": wk,
        "bod_year": yr,
        "bod_month": int(week.get("month") or 0),
        "bod_month_name": week.get("month_name") or "",
        "bod_label": label,
        "bod_source_mtime": float(week.get("source_mtime") or 0),
        "bod_sort_key": yr * 100 + wk,
        "bod_article_count": len(articles),
        "bod_preview_titles": json.dumps(
            [a["title"] for a in articles[:3] if a.get("title")], ensure_ascii=False
        ),
    }

    existing = wp.find_by_slug("/bod_issue", slug, status="publish,draft")
    if existing:
        issue_id = existing["id"]
        wp.post(f"/bod_issue/{issue_id}", {"title": label, "meta": issue_meta})
    else:
        created = wp.post(
            "/bod_issue",
            {"title": label, "slug": slug, "status": "publish", "meta": issue_meta},
        )
        issue_id = created.get("id", 0)

    if not issue_id:
        if wp.dry_run:
            issue_id = 0
        else:
            print("    ! no issue id, skipping children")
            return

    # Replace children so re-runs stay idempotent (mirrors build.py _upsert_week).
    if issue_id:
        for child_type in ("bod_story", "bod_release"):
            for child in wp.paginate(f"/{child_type}", parent=issue_id, status="publish,draft"):
                wp.delete(f"/{child_type}/{child['id']}", force=True)

    for kind, items in (("article", articles), ("paper", papers)):
        for position, item in enumerate(items, start=1):
            technologies = as_list(item.get("technologies"))

            tech_ids = []
            for tech in technologies:
                tslug = build._slugify(tech)
                if not tslug:
                    continue
                term_id = techs.id_for(tech, tslug)
                if term_id:
                    tech_ids.append(term_id)

            beat_ids = []
            category = item.get("category")
            if category:
                beat_id = beats.id_for(item.get("category_label") or category, category)
                if beat_id:
                    beat_ids.append(beat_id)

            payload = {
                "title": item.get("title") or "",
                "slug": item.get("slug") or "",
                "status": "publish",
                "parent": issue_id,
                "menu_order": position,
                "meta": {
                    "bod_kind": kind,
                    "bod_position": position,
                    "bod_url": item.get("url") or "",
                    "bod_source": item.get("source") or "",
                    "bod_published": item.get("published") or "",
                    "bod_short_summary": item.get("short_summary") or "",
                    "bod_main_topic": item.get("main_topic") or "",
                    "bod_long_resume_paragraphs": json.dumps(
                        as_list(item.get("long_resume_paragraphs")), ensure_ascii=False
                    ),
                    "bod_technologies": json.dumps(technologies, ensure_ascii=False),
                    "bod_category": category or "",
                    "bod_category_label": item.get("category_label") or "",
                    "bod_quality_score": float(item.get("quality_score") or 0),
                    "bod_week": wk,
                    "bod_year": yr,
                    "bod_sort_key": yr * 100 + wk,
                },
            }
            if beat_ids:
                payload["bod_beat"] = beat_ids
            if tech_ids:
                payload["bod_tech"] = tech_ids

            wp.post("/bod_story", payload)

    for position, release in enumerate(releases, start=1):
        wp.post(
            "/bod_release",
            {
                "title": release.get("model_name") or "",
                "slug": release.get("slug") or "",
                "status": "publish",
                "parent": issue_id,
                "menu_order": position,
                "meta": {
                    "bod_position": position,
                    "bod_provider": release.get("provider") or "",
                    "bod_model_name": release.get("model_name") or "",
                    "bod_release_date": release.get("release_date") or "",
                    "bod_summary": release.get("summary") or "",
                    "bod_url": release.get("url") or "",
                    "bod_key_features": json.dumps(
                        as_list(release.get("key_features")), ensure_ascii=False
                    ),
                    "bod_week": wk,
                    "bod_year": yr,
                },
            },
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print writes without sending them")
    parser.add_argument("--limit", type=int, default=0, help="only the N newest weeks")
    parser.add_argument("--week", type=int, help="restrict to one ISO week (with --year)")
    parser.add_argument("--year", type=int, help="restrict to one year")
    parser.add_argument(
        "--purge",
        action="store_true",
        help="delete every bod_issue/bod_story/bod_release first (clears orphans "
        "left by an interrupted or faulty run before rebuilding from scratch)",
    )
    parser.add_argument(
        "--manifest",
        default=str(ROOT / "weeks_manifest.json"),
        metavar="PATH",
        help="path to the weeks manifest (default: weeks_manifest.json at the repo root)",
    )
    args = parser.parse_args()

    wp = WPClient(dry_run=args.dry_run)
    me = wp.whoami()
    print(f"Target {wp.site} as {me.get('name')}")
    wp.require_theme()
    if args.dry_run:
        print("DRY RUN — no writes will be sent")

    source = Path(args.manifest)
    if not source.exists():
        print(f"No manifest at {source}")
        return 1
    weeks = json.loads(source.read_text(encoding="utf-8"))
    # Push newest-first so a partial or interrupted run still covers recent issues.
    weeks.sort(key=lambda w: (int(w["year"]), int(w["week"])), reverse=True)
    print(f"Source: {source.name} ({len(weeks)} weeks)")

    if args.week and args.year:
        weeks = [w for w in weeks if int(w["week"]) == args.week and int(w["year"]) == args.year]
    if args.limit:
        weeks = weeks[: args.limit]

    if not weeks:
        print("No weeks matched.")
        return 1

    if args.purge:
        print("\n[purge] removing all existing issue content")
        for post_type in ("bod_story", "bod_release", "bod_issue"):
            removed = 0
            while True:
                batch = list(wp.paginate(f"/{post_type}", per_page=100, status="publish,draft,trash"))
                if not batch:
                    break
                for item in batch:
                    try:
                        wp.delete(f"/{post_type}/{item['id']}", force=True)
                        removed += 1
                    except WPError as exc:
                        print(f"    ! {post_type}/{item['id']}: {exc}")
                if wp.dry_run:
                    break
            print(f"  {post_type}: {removed} deleted")

    print(f"\nBackfilling {len(weeks)} week(s)\n")

    beats = TermCache(wp, "bod_beat")
    techs = TermCache(wp, "bod_tech")
    if not args.dry_run:
        beats.prime()
        techs.prime()

    for index, week in enumerate(weeks, start=1):
        print(f"[{index}/{len(weeks)}]", end=" ")
        try:
            push_week(wp, week, beats, techs)
        except WPError as exc:
            print(f"    ! week failed: {exc}")

    print("\nDone. Check /archive.html on the mirror.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
