#!/usr/bin/env python3
"""Minimal WordPress REST client for the Altervista mirror.

Shared by scripts/wp_migrate.py and scripts/wp_backfill.py. Deliberately
stdlib-only and modelled on maki_newsletter/publish.py, which already talks to
this same install — same auth (Application Password over Basic), same base URL.

Credentials come from the environment, falling back to maki_newsletter/.env:

    ALTERVISTA_SITE_URL       https://bowlofdata.altervista.org/
    ALTERVISTA_USERNAME       wp admin username
    ALTERVISTA_APP_PASSWORD   wp Application Password ("xxxx xxxx ...")
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILES = [
    ROOT / ".env",
    ROOT.parent / "maki_newsletter" / ".env",
]

USER_AGENT = "BowlOfData-Migrate/1.0"
TIMEOUT = 45


class WPError(RuntimeError):
    """A non-2xx response from the WordPress REST API."""

    def __init__(self, status: int, body: Any, url: str):
        self.status = status
        self.body = body
        self.url = url
        detail = body.get("message") if isinstance(body, dict) else body
        super().__init__(f"HTTP {status} for {url}: {detail}")


def load_env(paths: list[Path] | None = None) -> dict[str, str]:
    """Read KEY=VALUE files without clobbering variables already set."""
    values: dict[str, str] = {}
    for path in paths if paths is not None else DEFAULT_ENV_FILES:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values.setdefault(key.strip(), value.strip().strip("\"'"))
    for key, value in values.items():
        os.environ.setdefault(key, value)
    return values


class WPClient:
    """Thin wrapper over /wp-json with pagination and dry-run support."""

    def __init__(self, dry_run: bool = False):
        load_env()
        site = os.environ.get("ALTERVISTA_SITE_URL", "").rstrip("/")
        user = os.environ.get("ALTERVISTA_USERNAME", "")
        password = os.environ.get("ALTERVISTA_APP_PASSWORD", "")

        missing = [
            name
            for name, value in (
                ("ALTERVISTA_SITE_URL", site),
                ("ALTERVISTA_USERNAME", user),
                ("ALTERVISTA_APP_PASSWORD", password),
            )
            if not value
        ]
        if missing:
            raise SystemExit(
                "Missing credentials: "
                + ", ".join(missing)
                + f"\nSet them in the environment or in one of: "
                + ", ".join(str(p) for p in DEFAULT_ENV_FILES)
            )

        self.site = site
        self.api = f"{site}/wp-json/wp/v2"
        self.dry_run = dry_run
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        self._auth = f"Basic {token}"

    # -- transport ---------------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        params: dict | None = None,
        base: str | None = None,
    ) -> Any:
        """One REST call. Writes are skipped (and logged) when dry_run is set."""
        url = (base or self.api) + path
        if params:
            url += "?" + urllib.parse.urlencode(params, doseq=True)

        if self.dry_run and method != "GET":
            keys = ", ".join(sorted(payload)) if payload else "-"
            print(f"    [dry-run] {method} {url}  ({keys})")
            return {"id": 0, "dry_run": True}

        data = None
        headers = {"Authorization": self._auth, "User-Agent": USER_AGENT}
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=data, headers=headers, method=method)

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                    body = response.read().decode()
                    return json.loads(body) if body else None
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode(errors="replace")
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = raw
                # 5xx is worth retrying; a 4xx will not fix itself.
                if exc.code < 500:
                    raise WPError(exc.code, parsed, url) from None
                last_error = WPError(exc.code, parsed, url)
            except urllib.error.URLError as exc:
                last_error = exc
            time.sleep(1.5 * (attempt + 1))

        raise last_error if last_error else RuntimeError("unreachable")

    def get(self, path: str, **params) -> Any:
        return self.request("GET", path, params=params or None)

    def post(self, path: str, payload: dict) -> Any:
        return self.request("POST", path, payload=payload)

    def delete(self, path: str, force: bool = False) -> Any:
        return self.request("DELETE", path, params={"force": "true"} if force else None)

    # -- helpers -----------------------------------------------------------

    def paginate(self, path: str, per_page: int = 100, **params) -> Iterator[dict]:
        """Yield every object across all pages of a collection endpoint."""
        page = 1
        while True:
            try:
                batch = self.get(path, per_page=per_page, page=page, **params)
            except WPError as exc:
                # WordPress 400s when you ask for a page past the end.
                if exc.status == 400:
                    return
                raise
            if not batch:
                return
            yield from batch
            if len(batch) < per_page:
                return
            page += 1

    def find_by_slug(self, path: str, slug: str, **params) -> dict | None:
        """First object with this exact slug, or None."""
        matches = self.get(path, slug=slug, per_page=1, **params)
        if isinstance(matches, list) and matches:
            return matches[0]
        return None

    def whoami(self) -> dict:
        return self.get("/users/me", context="edit")

    def require_theme(self) -> None:
        """Fail early and clearly if the child theme is not active yet.

        The bod_* routes only exist once inc/content.php has run, so without
        this every call downstream fails with an opaque "No route was found".
        """
        routes = self.request("GET", "", base=f"{self.site}/wp-json") or {}
        if "/wp/v2/bod_issue" in (routes.get("routes") or {}):
            return
        raise SystemExit(
            "The Bowl of Data child theme is not active on "
            f"{self.site} — the bod_issue REST route is missing.\n"
            "Build and upload it first:\n"
            "  python3 scripts/build_wp_theme.py\n"
            "  wp-admin -> Appearance -> Themes -> Add New -> Upload Theme -> Activate"
        )


def confirm(prompt: str) -> bool:
    """Interactive yes/no. Returns False on EOF (non-interactive runs)."""
    try:
        return input(f"{prompt} [y/N] ").strip().lower() in {"y", "yes"}
    except EOFError:
        return False
