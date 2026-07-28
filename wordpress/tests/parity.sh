#!/usr/bin/env bash
#
# Markup parity guard for the WordPress port.
#
# Renders the same article through netlify/functions/_shared/render.mjs (the
# source of truth) and through the theme's inc/render.php, then diffs them.
# Two differences are expected and normalised away:
#
#   * host      — the PHP port emits absolute URLs, render.mjs relative ones
#   * "../"     — render.mjs threads a directory prefix; WordPress routes
#
# Anything else is a real divergence between the two renderers.
#
# Usage: wordpress/tests/parity.sh

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

command -v node >/dev/null || { echo "node is required"; exit 1; }
command -v php  >/dev/null || { echo "php is required (brew install php)"; exit 1; }

node "$here/render_js.mjs"  > "$work/js.html"
php  "$here/render_php.php" > "$work/php.html"

normalise() {
  sed -e 's|https://bowlofdata.altervista.org/||g' -e 's|\.\./||g' "$1" \
    | tr -s ' \t\n' ' ' \
    | sed -e 's/> </></g' -e 's/^ //' -e 's/ $//'
}

normalise "$work/js.html"  > "$work/js.norm"
normalise "$work/php.html" > "$work/php.norm"

if diff -q "$work/js.norm" "$work/php.norm" >/dev/null; then
  echo "PASS  article card markup is identical (render.mjs == inc/render.php)"
  exit 0
fi

echo "FAIL  renderers diverged:"
diff <(fold -w110 "$work/js.norm") <(fold -w110 "$work/php.norm") || true
exit 1
