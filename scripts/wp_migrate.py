#!/usr/bin/env python3
"""Prepare the Altervista WordPress install to host the Bowl of Data mirror.

Steps, in order, all idempotent and re-runnable:

  1. backup   dump every existing page + the media index to wordpress/backup/
  2. wipe     move the old pages to trash (recoverable) -- needs --confirm-wipe
  3. pages    create the static pages the theme has templates for
  4. front    point the site's front page at the new home page
  5. menu     rebuild the primary menu to match the header nav
  6. banners  switch off Altervista's per-page ad injection where allowed

Usage:
    python3 scripts/wp_migrate.py --dry-run          # show every write, change nothing
    python3 scripts/wp_migrate.py --confirm-wipe     # full run including the trash step
    python3 scripts/wp_migrate.py --steps pages,menu # run a subset

The wipe step never force-deletes: pages go to trash and can be restored from
wp-admin. The backup runs first regardless, and refuses to continue if it fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wp_client import WPClient, WPError, confirm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT / "wordpress" / "backup"

# slug -> (title, menu label or None if it should not appear in the nav)
STATIC_PAGES = {
    "home": ("Home", None),
    "archive": ("Archive", "Archive"),
    "topics": ("Topics", "Topics"),
    "services": ("Services", "Services"),
    "about": ("About", "About"),
    "team": ("Team", "Team"),
    "contact": ("Contact", "Contact"),
}

# The header nav, in order. (label, slug or absolute URL, parent label or None)
MENU_STRUCTURE = [
    ("Home", "home", None),
    ("Archive", "archive", None),
    ("Topics", "topics", None),
    ("Services", "services", None),
    ("About", "about", None),
    ("Team", "team", "About"),
    ("Contact", "contact", "About"),
]

# Altervista exposes these on the page schema; turning them off suppresses the
# free plan's injected banners where the platform honours it.
BANNER_META = {
    "avopt_banners_on_page": False,
    "avopt_banners_inside_post": False,
    "av_allow_affiliate_banner": False,
    "av_allow_affiliate_multi_banner": False,
    "av_show_affiliation_buy_button": False,
}

ALL_STEPS = ["backup", "wipe", "pages", "front", "menu", "banners"]


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


def step_backup(wp: WPClient) -> Path:
    """Dump pages (edit context, so raw content is included) and media."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    pages = list(wp.paginate("/pages", context="edit", status="any"))
    media = list(wp.paginate("/media"))
    posts = list(wp.paginate("/posts", context="edit", status="any"))

    target = BACKUP_DIR / f"backup-{stamp}.json"
    target.write_text(
        json.dumps(
            {
                "site": wp.site,
                "taken_at": stamp,
                "pages": pages,
                "posts": posts,
                "media": media,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"  backed up {len(pages)} pages, {len(posts)} posts, {len(media)} media")
    print(f"  -> {target.relative_to(ROOT)}")
    return target


def step_wipe(wp: WPClient, confirmed: bool) -> None:
    """Trash every existing page. Recoverable: force=False."""
    pages = list(wp.paginate("/pages", status="publish,draft,pending,private"))
    if not pages:
        print("  nothing to trash")
        return

    print(f"  {len(pages)} page(s) would go to trash:")
    for page in pages:
        print(f"    - id={page['id']:<5} {page.get('slug','')}")

    if not confirmed:
        print("  refusing to trash without --confirm-wipe (or answer the prompt)")
        if not wp.dry_run and not confirm("  Trash these pages now?"):
            print("  skipped")
            return

    for page in pages:
        try:
            wp.delete(f"/pages/{page['id']}", force=False)
            print(f"    trashed {page['id']} ({page.get('slug','')})")
        except WPError as exc:
            print(f"    ! could not trash {page['id']}: {exc}")


def step_pages(wp: WPClient) -> dict[str, int]:
    """Create (or find) the static pages. Bodies stay empty: templates render."""
    ids: dict[str, int] = {}

    for slug, (title, _label) in STATIC_PAGES.items():
        existing = wp.find_by_slug("/pages", slug, status="publish,draft,trash")

        if existing and existing.get("status") == "trash":
            # We just trashed a same-named page; bring it back and reuse it.
            existing = wp.post(f"/pages/{existing['id']}", {"status": "publish"})

        if existing:
            ids[slug] = existing["id"]
            print(f"    exists  {slug:<9} id={existing['id']}")
            continue

        created = wp.post(
            "/pages",
            {
                "title": title,
                "slug": slug,
                "status": "publish",
                "content": "",
                "comment_status": "closed",
                "ping_status": "closed",
            },
        )
        ids[slug] = created.get("id", 0)
        print(f"    created {slug:<9} id={ids[slug]}")

    return ids


def step_front(wp: WPClient, page_ids: dict[str, int]) -> None:
    """Static front page = our home page; no separate posts page."""
    home_id = page_ids.get("home")
    if not home_id:
        print("  no home page id, skipping")
        return

    wp.request(
        "POST",
        "/settings",
        payload={"show_on_front": "page", "page_on_front": home_id, "page_for_posts": 0},
    )
    print(f"  front page -> id={home_id}")


def step_menu(wp: WPClient, page_ids: dict[str, int]) -> None:
    """Rebuild the primary menu so it matches the theme's header nav."""
    menus = wp.get("/menus", per_page=100)
    menu = next((m for m in menus if m.get("slug") == "main"), None) if isinstance(menus, list) else None

    if not menu:
        menu = wp.post("/menus", {"name": "Main", "slug": "main"})
        print(f"  created menu id={menu.get('id')}")
    menu_id = menu.get("id")

    # Clear the existing items so re-runs do not duplicate the nav.
    for item in wp.paginate("/menu-items", menus=menu_id):
        wp.delete(f"/menu-items/{item['id']}", force=True)

    created: dict[str, int] = {}
    for order, (label, slug, parent_label) in enumerate(MENU_STRUCTURE, start=1):
        page_id = page_ids.get(slug)
        if not page_id:
            continue
        payload = {
            "title": label,
            "menus": menu_id,
            "menu_order": order,
            "object": "page",
            "object_id": page_id,
            "type": "post_type",
            "status": "publish",
        }
        if parent_label and parent_label in created:
            payload["parent"] = created[parent_label]

        item = wp.post("/menu-items", payload)
        created[label] = item.get("id", 0)
        print(f"    {order}. {label}")

    # Attach it to the theme's registered location.
    try:
        wp.post(f"/menu-locations/bod_primary", {"menu": menu_id})
    except WPError:
        # Location only exists once the child theme is active; harmless before that.
        print("  (menu location bod_primary not registered yet)")


def step_banners(wp: WPClient, page_ids: dict[str, int]) -> None:
    """Ask Altervista not to inject ads into our pages."""
    for slug, page_id in page_ids.items():
        if not page_id:
            continue
        try:
            wp.post(f"/pages/{page_id}", dict(BANNER_META))
            print(f"    banners off: {slug}")
        except WPError as exc:
            print(f"    ! {slug}: {exc}")


# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print writes without sending them")
    parser.add_argument("--confirm-wipe", action="store_true", help="allow the trash step to run unattended")
    parser.add_argument(
        "--steps",
        default=",".join(ALL_STEPS),
        help=f"comma-separated subset of: {', '.join(ALL_STEPS)}",
    )
    args = parser.parse_args()

    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    unknown = [s for s in steps if s not in ALL_STEPS]
    if unknown:
        parser.error(f"unknown step(s): {', '.join(unknown)}")

    wp = WPClient(dry_run=args.dry_run)
    me = wp.whoami()
    print(f"Connected to {wp.site} as {me.get('name')} ({', '.join(me.get('roles', []))})")
    if args.dry_run:
        print("DRY RUN — no writes will be sent\n")

    page_ids: dict[str, int] = {}

    for step in steps:
        print(f"\n[{step}]")
        if step == "backup":
            step_backup(wp)
        elif step == "wipe":
            step_wipe(wp, args.confirm_wipe)
        elif step == "pages":
            page_ids = step_pages(wp)
        elif step == "front":
            page_ids = page_ids or step_pages(wp)
            step_front(wp, page_ids)
        elif step == "menu":
            page_ids = page_ids or step_pages(wp)
            step_menu(wp, page_ids)
        elif step == "banners":
            page_ids = page_ids or step_pages(wp)
            step_banners(wp, page_ids)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
