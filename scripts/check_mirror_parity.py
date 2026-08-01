#!/usr/bin/env python3
"""Diff the WordPress mirror's sitemap against the canonical one.

The mirror and bowlofdata.net publish the same pages at the same paths, so
their sitemaps must list the same set. When they drift, one of two things has
gone wrong, and both have happened in production:

  only on the mirror  -> it advertises a URL with no page behind it. Yoast used
                         to list all 1,401 bod_tech terms while the theme 404s
                         anything under BOD_MIN_TAG_ITEMS, so ~1,270 sitemap
                         entries answered 404.
  only on .net        -> the mirror is stale; the weekly wp_sync did not land.

    python3 scripts/check_mirror_parity.py
    python3 scripts/check_mirror_parity.py --check-status      # sample for 404s
    python3 scripts/check_mirror_parity.py --check-status --sample 40

Exits non-zero on any difference, so it works as a post-deploy gate.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
LOCAL_SITEMAP = ROOT / "site" / "sitemap.xml"
MIRROR_SITEMAP = "https://bowlofdata.altervista.org/sitemap.xml"

USER_AGENT = "bowlofdata-parity-check"
TIMEOUT = 30


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", errors="replace")


def paths(sitemap_xml: str) -> set[str]:
    """The <loc> entries reduced to origin-relative paths, so the two domains compare."""
    return {
        urlparse(loc).path or "/"
        for loc in re.findall(r"<loc>([^<]+)</loc>", sitemap_xml)
    }


def status_of(url: str) -> int:
    request = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except urllib.error.URLError:
        return 0


def report(label: str, missing: set[str], limit: int = 15) -> None:
    listed = sorted(missing)
    print(f"\n  {len(listed)} path(s) {label}:")
    for path in listed[:limit]:
        print(f"    {path}")
    if len(listed) > limit:
        print(f"    … and {len(listed) - limit} more")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mirror", default=MIRROR_SITEMAP, help="mirror sitemap URL")
    parser.add_argument(
        "--check-status",
        action="store_true",
        help="HEAD-request a sample of mirror URLs and assert they answer 200",
    )
    parser.add_argument(
        "--sample", type=int, default=25, help="how many URLs to probe (default 25)"
    )
    args = parser.parse_args()

    if not LOCAL_SITEMAP.exists():
        print(f"No {LOCAL_SITEMAP.relative_to(ROOT)} — run build.py first.", file=sys.stderr)
        return 2

    canonical = paths(LOCAL_SITEMAP.read_text(encoding="utf-8"))
    try:
        mirror_xml = fetch(args.mirror)
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        print(f"Could not fetch {args.mirror}: {exc}", file=sys.stderr)
        return 2

    mirror = paths(mirror_xml)
    print(f"canonical  {len(canonical):>5} paths  ({LOCAL_SITEMAP.relative_to(ROOT)})")
    print(f"mirror     {len(mirror):>5} paths  ({args.mirror})")

    phantom = mirror - canonical
    stale = canonical - mirror
    failed = False

    if phantom:
        report("on the mirror only (no page behind them)", phantom)
        failed = True
    if stale:
        report("on bowlofdata.net only (mirror is behind)", stale)
        failed = True

    if args.check_status and mirror:
        ordered = sorted(mirror)
        step = max(1, len(ordered) // args.sample)
        sample = ordered[::step][: args.sample]
        origin = f"{urlparse(args.mirror).scheme}://{urlparse(args.mirror).netloc}"

        bad: list[tuple[str, int]] = []
        for path in sample:
            code = status_of(origin + path)
            if code != 200:
                bad.append((path, code))

        print(f"\nprobed {len(sample)} mirror URL(s): {len(sample) - len(bad)} x 200")
        for path, code in bad[:15]:
            print(f"    {code}  {path}")
        if bad:
            failed = True

    if failed:
        print("\nFAIL — the two sitemaps disagree.")
        return 1

    print("\nOK — both sitemaps describe the same pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
