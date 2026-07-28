#!/usr/bin/env python3
"""Assemble the WordPress child theme into an uploadable ZIP.

The theme's PHP lives in wordpress/bowlofdata-child/, but its stylesheet and
images are the website's own: static/style.css and imgs/ are the single source
of truth and get copied in here rather than duplicated in the repo.

    python3 scripts/build_wp_theme.py            # -> wordpress/dist/bowlofdata-child.zip
    python3 scripts/build_wp_theme.py --no-zip   # leave the staged directory only

Upload the ZIP in wp-admin -> Appearance -> Themes -> Add New -> Upload Theme.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "wordpress" / "bowlofdata-child"
DIST = ROOT / "wordpress" / "dist"
STAGE = DIST / "bowlofdata-child"
ZIP_PATH = DIST / "bowlofdata-child.zip"

STYLE_HEADER = SRC / "style.header.css"
STYLE_SOURCE = ROOT / "static" / "style.css"
IMGS_SOURCE = ROOT / "imgs"

# Only these images are referenced by the templates.
THEME_IMAGES = [
    "logo.png",
    "bowl.png",
    "bowl-hero.png",
    "marco.jpg",
    "luigi.jpg",
    "maki_logo.png",
]


def build_stylesheet() -> str:
    """Theme header + the design system, concatenated."""
    header = STYLE_HEADER.read_text(encoding="utf-8").rstrip()
    design = STYLE_SOURCE.read_text(encoding="utf-8")
    return f"{header}\n\n{design}"


def stage() -> list[Path]:
    """Copy the PHP, generated stylesheet and images into a clean directory."""
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    copied: list[Path] = []

    for php in sorted(SRC.rglob("*.php")):
        target = STAGE / php.relative_to(SRC)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(php, target)
        copied.append(target)

    (STAGE / "style.css").write_text(build_stylesheet(), encoding="utf-8")
    copied.append(STAGE / "style.css")

    imgs = STAGE / "imgs"
    imgs.mkdir()
    for name in THEME_IMAGES:
        source = IMGS_SOURCE / name
        if not source.exists():
            print(f"  ! missing image {source}", file=sys.stderr)
            continue
        shutil.copy2(source, imgs / name)
        copied.append(imgs / name)

    return copied


def lint(files: list[Path]) -> bool:
    """Run `php -l` over the staged PHP when a php binary is available."""
    php = shutil.which("php")
    if not php:
        print("  · php not installed, skipping syntax check")
        return True

    ok = True
    for path in files:
        if path.suffix != ".php":
            continue
        result = subprocess.run(
            [php, "-l", str(path)], capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            ok = False
            print(f"  ✗ {path.relative_to(STAGE)}", file=sys.stderr)
            print(result.stdout.strip() or result.stderr.strip(), file=sys.stderr)
    if ok:
        print("  · php -l clean")
    return ok


def make_zip() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(STAGE.rglob("*")):
            if path.is_file():
                zf.write(path, Path("bowlofdata-child") / path.relative_to(STAGE))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-zip", action="store_true", help="stage only, do not archive")
    args = parser.parse_args()

    print(f"Staging theme in {STAGE.relative_to(ROOT)}")
    copied = stage()
    php_count = sum(1 for p in copied if p.suffix == ".php")
    css_size = (STAGE / "style.css").stat().st_size
    print(f"  · {php_count} php files, style.css {css_size:,} bytes")

    if not lint(copied):
        print("Syntax errors — not packaging.", file=sys.stderr)
        return 1

    if args.no_zip:
        return 0

    make_zip()
    print(f"  · {ZIP_PATH.relative_to(ROOT)} ({ZIP_PATH.stat().st_size:,} bytes)")
    print("\nUpload it: wp-admin -> Appearance -> Themes -> Add New -> Upload Theme")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
