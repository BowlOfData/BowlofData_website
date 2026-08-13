#!/usr/bin/env python3
"""Assert the retired WordPress mirror 301s to bowlofdata.net.

The mirror at bowlofdata.altervista.org existed only because bowlofdata.net —
an Aruba domain-forward at the time — could not serve deep paths. Once .net was
pointed at Netlify (2026-08-12) the two installs published identical titles and
identical sitemaps at identical paths, splitting the authority for every query.
The mirror was retired: BOD_RETIRED_TO in the child theme 301s every front-end
request to its .net twin.

This script used to diff the two sitemaps for parity. That question is dead —
there is only one site now. What matters is that the retirement is actually in
force and pointing at the right places, which is what it checks instead:

  every sampled path  -> 301, Location = the same path on bowlofdata.net
  /robots.txt         -> 200, still crawlable

robots.txt is the one exemption that matters. WordPress serves it through the
template loader *after* template_redirect fires, so an unguarded blanket
redirect swallows it too — and a crawler that cannot fetch robots.txt never
crawls the pages, never sees the 301s, and never consolidates anything. A
redirected or missing robots.txt fails this check loudly for that reason.

    python3 scripts/check_mirror_parity.py
    python3 scripts/check_mirror_parity.py --sample 40
    python3 scripts/check_mirror_parity.py --no-probe    # offline: list what would be checked

Exits non-zero on any path that is not correctly retired, so it works as a
post-deploy gate.
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
MIRROR_ORIGIN = "https://bowlofdata.altervista.org"
CANONICAL_ORIGIN = "https://bowlofdata.net"

USER_AGENT = "bowlofdata-retirement-check"
TIMEOUT = 30

# Probing is bounded so a mass divergence cannot turn one check into hundreds
# of requests against a shared host.
DEFAULT_SAMPLE = 25


def paths(sitemap_xml: str) -> set[str]:
    """The <loc> entries reduced to origin-relative paths."""
    return {
        urlparse(loc).path or "/"
        for loc in re.findall(r"<loc>([^<]+)</loc>", sitemap_xml)
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Report the 301 rather than following it — the Location is the point."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_opener = urllib.request.build_opener(NoRedirect)


def head(url: str) -> tuple[int, str | None]:
    """(status, Location) for a HEAD, without following redirects."""
    request = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": USER_AGENT}
    )
    try:
        with _opener.open(request, timeout=TIMEOUT) as response:
            return response.status, response.headers.get("Location")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Location")
    except urllib.error.URLError:
        return 0, None


def check_robots() -> str | None:
    """None when robots.txt is healthy, else the reason it is not."""
    status, location = head(f"{MIRROR_ORIGIN}/robots.txt")
    if status != 200:
        return (
            f"robots.txt answered {status}"
            + (f" -> {location}" if location else "")
            + " — it must stay 200. A crawler that cannot read it never fetches"
            " the pages and never sees the 301s, so consolidation stalls."
        )
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mirror", default=MIRROR_ORIGIN, help="retired origin")
    parser.add_argument(
        "--sample", type=int, default=DEFAULT_SAMPLE,
        help=f"how many paths to probe (default {DEFAULT_SAMPLE})",
    )
    parser.add_argument(
        "--no-probe", action="store_true",
        help="list the paths that would be checked and stop (no network)",
    )
    args = parser.parse_args()

    if not LOCAL_SITEMAP.exists():
        print(f"No {LOCAL_SITEMAP.relative_to(ROOT)} — run build.py first.", file=sys.stderr)
        return 2

    canonical = sorted(paths(LOCAL_SITEMAP.read_text(encoding="utf-8")))
    step = max(1, len(canonical) // args.sample)
    sample = canonical[::step][: args.sample]

    print(f"canonical  {len(canonical):>5} paths  ({LOCAL_SITEMAP.relative_to(ROOT)})")
    print(f"retiring   {args.mirror} -> {CANONICAL_ORIGIN}")
    print(f"sampling   {len(sample)} path(s)\n")

    if args.no_probe:
        for path in sample:
            print(f"    would check {args.mirror}{path}")
        return 0

    failures: list[str] = []

    reason = check_robots()
    if reason:
        failures.append(reason)
    else:
        print("  ok    /robots.txt  200, still crawlable")

    for path in sample:
        status, location = head(args.mirror + path)
        expected = CANONICAL_ORIGIN + path
        if status != 301:
            failures.append(f"{path} answered {status}, expected 301")
        elif (location or "").rstrip("/") != expected.rstrip("/"):
            failures.append(f"{path} redirects to {location}, expected {expected}")

    checked = len(sample)
    print(f"  {checked - len([f for f in failures if not f.startswith('robots')])}"
          f"/{checked} sampled path(s) 301 to their .net twin")

    if failures:
        print(f"\nFAIL — {len(failures)} problem(s):")
        for failure in failures[:15]:
            print(f"    {failure}")
        if len(failures) > 15:
            print(f"    … and {len(failures) - 15} more")
        return 1

    print("\nOK — the mirror is retired and pointing at the canonical site.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
