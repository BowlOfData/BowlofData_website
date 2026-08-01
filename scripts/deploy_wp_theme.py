#!/usr/bin/env python3
"""Install the built child theme on the Altervista mirror, over REST.

Two host quirks rule out the obvious routes (see README): wp-admin's "Upload
Theme" form does not work on this install, and PHP cannot fetch URLs on its own
domain, so Theme_Upgrader cannot pull the ZIP from a link. What does work is
handing Theme_Upgrader a *local* path — which means the ZIP has to reach the
server through the media library first, and the install has to run as PHP
inside WordPress. This script automates that dance end to end:

    1. upload wordpress/dist/bowlofdata-child.zip to the media library
    2. activate Code Snippets, which is installed for exactly this
    3. run a single-use snippet: Theme_Upgrader->install( local path )
    4. clear the rewrite rules so the NEXT request rebuilds them with the new
       code — flushing in-process would rebuild from the theme still in memory
    5. tear it all down: snippet, plugin, attachment, log file

    python3 scripts/build_wp_theme.py && python3 scripts/deploy_wp_theme.py
    python3 scripts/deploy_wp_theme.py --keep-plugin   # leave Code Snippets on

Credentials come from the environment or ../maki_newsletter/.env, same as
wp_migrate.py — see wp_client.WPClient.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wp_client import WPClient, WPError, load_env  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ZIP_PATH = ROOT / "wordpress" / "dist" / "bowlofdata-child.zip"
THEME = "bowlofdata-child"
PLUGIN = "code-snippets/code-snippets"
LOG_NAME = "bod-deploy-result.txt"

# Verified after install: sizes must match what we just built, which proves the
# new files landed rather than the old ones surviving an overwrite that no-oped.
CHECK_FILES = ["inc/seo.php", "index.php", "inc/render.php", "functions.php"]

INSTALL_SNIPPET = """
$up  = wp_upload_dir();
$zip = $up['basedir'] . '/%(subdir)s/%(filename)s';
$log = array( 'exists: ' . ( file_exists( $zip ) ? 'yes' : 'no' ) );

if ( file_exists( $zip ) ) {
    require_once ABSPATH . 'wp-admin/includes/file.php';
    require_once ABSPATH . 'wp-admin/includes/misc.php';
    require_once ABSPATH . 'wp-admin/includes/class-wp-upgrader.php';

    $upgrader = new Theme_Upgrader( new Automatic_Upgrader_Skin() );
    $ok = $upgrader->install( $zip, array( 'overwrite_package' => true ) );
    $log[] = 'install: ' . ( is_wp_error( $ok ) ? 'WP_Error ' . $ok->get_error_message() : var_export( $ok, true ) );

    $root = get_theme_root() . '/%(theme)s';
    foreach ( %(files)s as $rel ) {
        $log[] = $rel . '=' . ( file_exists( "$root/$rel" ) ? filesize( "$root/$rel" ) : 'MISSING' );
    }

    // Regenerate on the next request, when the new code is loaded. Flushing
    // here would rebuild from the rules the running theme registered.
    delete_option( 'rewrite_rules' );
    delete_transient( 'bod_sitemap_xml' );
}
$log[] = 'theme: ' . get_option( 'stylesheet' );
$log[] = 'at: ' . gmdate( 'c' );
file_put_contents( $up['basedir'] . '/%(log)s', implode( "\\n", $log ) );
"""

CLEANUP_SNIPPET = """
$up = wp_upload_dir();
$f  = $up['basedir'] . '/%(log)s';
if ( file_exists( $f ) ) { @unlink( $f ); }
delete_transient( 'bod_sitemap_xml' );
"""


def upload_zip(client: WPClient, values: dict) -> dict:
    """POST the ZIP to /wp/v2/media, replacing any attachment of the same name."""
    for existing in client.paginate("/media", search=ZIP_PATH.stem, media_type=None):
        if existing.get("title", {}).get("rendered", "").startswith(ZIP_PATH.stem):
            client.delete(f"/media/{existing['id']}", force=True)
            print(f"  · replaced attachment {existing['id']}")

    data = ZIP_PATH.read_bytes()
    token = base64.b64encode(
        f"{values['ALTERVISTA_USERNAME']}:{values['ALTERVISTA_APP_PASSWORD']}".encode()
    ).decode()
    request = urllib.request.Request(
        f"{client.site}/wp-json/wp/v2/media",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/zip",
            "Content-Disposition": f'attachment; filename="{ZIP_PATH.name}"',
            "User-Agent": "BowlOfData-Deploy/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        body = json.loads(response.read().decode())
    print(f"  · uploaded {len(data):,} bytes -> attachment {body['id']}")
    return body


def run_snippet(client: WPClient, code: str, name: str) -> int:
    """Create a single-use snippet, run it once, and delete it."""
    base = f"{client.site}/wp-json/code-snippets/v1"
    snippet = client.request(
        "POST",
        "/snippets",
        payload={
            "name": name,
            "desc": "Created by scripts/deploy_wp_theme.py. Safe to delete.",
            "code": code,
            "scope": "single-use",
            "active": False,
            "priority": 10,
        },
        base=base,
    )
    if snippet.get("code_error"):
        raise SystemExit(f"Snippet rejected: {snippet['code_error']}")

    client.request("POST", f"/snippets/{snippet['id']}/activate", payload={}, base=base)
    time.sleep(3)
    try:
        client.request("DELETE", f"/snippets/{snippet['id']}", base=base)
    except WPError as exc:
        print(f"  ! snippet {snippet['id']} not deleted: {exc}", file=sys.stderr)
    return snippet["id"]


def read_log(client: WPClient) -> str:
    url = f"{client.site}/wp-content/uploads/{LOG_NAME}?cb={int(time.time())}"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "BowlOfData-Deploy/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode(errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        return f"(could not read deploy log: {exc})"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-plugin", action="store_true",
                        help="leave Code Snippets active afterwards")
    args = parser.parse_args()

    if not ZIP_PATH.exists():
        print(f"No {ZIP_PATH.relative_to(ROOT)} — run scripts/build_wp_theme.py first.",
              file=sys.stderr)
        return 2

    expected = {
        rel: (ROOT / "wordpress" / "dist" / THEME / rel).stat().st_size
        for rel in CHECK_FILES
    }

    values = load_env()
    client = WPClient()
    print(f"Deploying to {client.site}")

    attachment = upload_zip(client, values)
    subdir = "/".join(attachment["source_url"].split("/uploads/")[1].split("/")[:-1])

    plugins_base = f"{client.site}/wp-json/wp/v2"
    client.request("PUT", f"/plugins/{PLUGIN}", payload={"status": "active"}, base=plugins_base)
    print("  · Code Snippets activated")

    try:
        run_snippet(
            client,
            INSTALL_SNIPPET % {
                "subdir": subdir,
                "filename": ZIP_PATH.name,
                "theme": THEME,
                "files": "array( " + ", ".join(f"'{f}'" for f in CHECK_FILES) + " )",
                "log": LOG_NAME,
            },
            "BOD deploy (auto)",
        )
        log = read_log(client)
        print("\n".join(f"  | {line}" for line in log.splitlines()))

        sizes = dict(
            part.split("=", 1)
            for part in log.split()
            if "=" in part and part.split("=", 1)[0] in expected
        )
        mismatched = [
            f"{rel}: server={sizes.get(rel, '?')} local={size}"
            for rel, size in expected.items()
            if sizes.get(rel) != str(size)
        ]

        run_snippet(client, CLEANUP_SNIPPET % {"log": LOG_NAME}, "BOD deploy cleanup (auto)")
    finally:
        if not args.keep_plugin:
            try:
                client.request("PUT", f"/plugins/{PLUGIN}", payload={"status": "inactive"},
                               base=plugins_base)
                print("  · Code Snippets deactivated")
            except WPError as exc:
                print(f"  ! could not deactivate Code Snippets: {exc}", file=sys.stderr)
        try:
            client.delete(f"/media/{attachment['id']}", force=True)
            print(f"  · attachment {attachment['id']} removed")
        except WPError as exc:
            print(f"  ! attachment {attachment['id']} left behind: {exc}", file=sys.stderr)

    if mismatched:
        print("\nFAIL — installed files do not match the build:", file=sys.stderr)
        for line in mismatched:
            print(f"  {line}", file=sys.stderr)
        return 1

    print("\nInstalled. Rewrite rules rebuild on the next request; verify with:")
    print("  python3 scripts/check_mirror_parity.py --check-status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
