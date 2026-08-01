[![Netlify Status](https://api.netlify.com/api/v1/badges/5b9d0b22-a375-46b3-897f-2d4951929886/deploy-status)](https://app.netlify.com/projects/bowofdata/deploys)
[![Substack](https://img.shields.io/badge/Substack-bowlofdata-orange?logo=substack&logoColor=white)](https://substack.com/@bowlofdata)
# Bowl of Data — Website

Website for the [Bowl of Data](https://bowlofdata.net) tech newsletter. **A plain static site** — every page is rendered ahead of time from Jinja2 templates into `site/` and committed to the repo. No database, no serverless functions, nothing to run at request time.

## Overview

Newsletter content comes from the `summaries_WW_YYYY.json` files produced by the [maki](https://github.com/bowlofdata/maki) pipeline. Because that output directory only keeps recent issues, every week the builder has ever seen is cached in **`weeks_manifest.json`** — that file is the archive's real source of truth and is committed alongside the built site.

```
maki output ──┐
              ├──> build.py ──> weeks_manifest.json  (archive of record)
manifest ─────┘              └─> site/               (what Netlify publishes)
```

One command does everything:

```bash
python3 build.py                  # render only what changed since the last run
FORCE_REBUILD=1 python3 build.py  # re-render every week in the manifest
```

Both `site/` and `weeks_manifest.json` are **committed**. Netlify has no build command — it just publishes `site/`.

---

## Pages

Every URL below is a real file on disk under `site/`.

| URL | Description |
|---|---|
| `index.html` | Landing — hero, latest issue, recent issues |
| `week/WW_YYYY.html` | Full issue — article cards, TL;DR, releases, papers, prev/next nav |
| `topic/<slug>.html` | One editorial beat (ai / governance / security / blockchain / engineering) |
| `tag/<slug>.html` | Every item tagged with a technology (≥ 3 items) |
| `archive.html` | Index of all issues, grouped year → month |
| `topics.html` | Index of every topic hub and tag page |
| `about/team/contact/services.html` | Marketing pages |
| `sitemap.xml`, `feed.xml`, `llms.txt`, `robots.txt` | Crawler + LLM surface |

---

## First-time setup

**Prerequisites:** Python 3.10+, and the `maki` repo cloned as a sibling directory.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

The builder looks for newsletter data in `../maki_newsletter/maki_newsletter/output/` by default; override with `MAKI_OUTPUT_DIR=/path/to/output`.

Preview locally by opening `site/index.html`, or serve the directory:

```bash
python3 -m http.server -d site 8000
```

---

## Full weekly workflow

```bash
# 1. Run the maki pipeline (in the maki repo) → summaries_WW_YYYY.json
python -m maki_newsletter.main
python -m maki_newsletter.generate

# 2. Build (in this repo). Only the new week and its neighbours re-render;
#    the landing page, archive, topic hubs, tag pages and feeds always do.
.venv/bin/python build.py

# 3. Deploy
git add site weeks_manifest.json
git commit -m "week WW YYYY"
git push        # Netlify publishes site/ as-is
```

---

## WordPress mirror (Altervista)

`bowlofdata.altervista.org` runs a WordPress port of this site.

> ⚠️ **The domain is not wired up the way this section used to claim.** It said Netlify
> stays primary and the mirror canonicals back to `bowlofdata.net`. As of 2026-08-01 that
> is not what is deployed:
>
> - `bowlofdata.net` resolves to `62.149.189.54` (Aruba), **not** Netlify, and 302-redirects
>   to `bowlofdata.altervista.org` **with the path stripped** — `/week/31_2026.html` lands
>   on the homepage. `/imgs/*` and `/feed.xml` do too, which is why `og:image`, the favicon
>   and the JSON-LD logo were all resolving to an HTML document.
> - The Netlify build is live and healthy at `bowofdata.netlify.app`; the custom domain was
>   never attached to it.
>
> Because a canonical pointing at a path-stripping redirect tells Google every page is a
> duplicate of the homepage, the WordPress install **now canonicalises to itself**.
> `BOD_CANONICAL_ORIGIN` in `wordpress/bowlofdata-child/functions.php` defaults to
> `home_url()`; set it back to `'https://bowlofdata.net'` to restore mirror behaviour once
> `.net` serves real paths. `BOD_IS_MIRROR` derives from it and switches the feed handling
> and canonical strategy together — nothing else needs editing.
>
> **To restore the intended architecture:** point `bowlofdata.net` at Netlify (replace
> Aruba's forward with Netlify's DNS records), then flip `BOD_CANONICAL_ORIGIN` back.

The mirror is a Blocksy child theme in `wordpress/bowlofdata-child/` that re-implements the layout in PHP and stores newsletter content as custom post types.

| This repo | WordPress |
|---|---|
| a week entry | `bod_issue` — `/week/30_2026.html` |
| `articles` / `papers` | `bod_story` (child of the issue, `bod_kind` = article \| paper) |
| `model_releases` | `bod_release` (child of the issue) |
| item `category` | `bod_beat` taxonomy — `/topic/ai.html` |
| item `technologies` | `bod_tech` taxonomy — `/tag/python.html` (≥ 3 items, as everywhere else) |

URLs match bowlofdata.net exactly, `.html` suffix included.

### Installing or updating the theme on Altervista

Two host quirks make the obvious routes fail, so follow this order:

- **wp-admin's "Upload Theme" form does not work** on this install.
- **PHP cannot fetch URLs on its own domain** — Altervista's egress proxy answers
  `cURL error 56: CONNECT tunnel failed, response 403`. So `Theme_Upgrader` cannot
  download the ZIP from a link, and WP-Cron/loopback requests fail for the same reason.
  Only wordpress.org is reachable, which is why plugins install normally.

What does work is handing `Theme_Upgrader` a **local path**, which is what the deploy
script automates:

```bash
python3 scripts/build_wp_theme.py      # build + lint + zip
python3 scripts/deploy_wp_theme.py     # upload, install, verify, tear down
```

`deploy_wp_theme.py` uploads the ZIP to the media library, activates **Code Snippets**
(left installed for exactly this), runs a single-use snippet that calls
`Theme_Upgrader->install()` on the local path, then removes the snippet, deactivates the
plugin and deletes the attachment. It compares the installed file sizes against the ones
just built and exits non-zero if they differ, so a silently no-oped overwrite fails loudly.

Two details it handles that a manual run gets wrong:

- It clears `rewrite_rules` rather than calling `flush_rewrite_rules()`. Flushing in the
  same request rebuilds from the theme already in memory — the *old* one — so a newly
  added rule such as `/sitemap.xml` would be missing until something else flushed.
- Rules therefore regenerate on the next front-end request. Hit any URL once after
  deploying.

Verify afterwards with `python3 scripts/check_mirror_parity.py --check-status`.

```bash
# Ordinary rebuild once the theme is installed

# Prepare the install: back up, wipe old pages, create pages + menu
.venv/bin/python scripts/wp_migrate.py --dry-run
.venv/bin/python scripts/wp_migrate.py --confirm-wipe

# Seed every historical issue from weeks_manifest.json (one time)
.venv/bin/python scripts/wp_backfill.py --limit 1     # check one week first
.venv/bin/python scripts/wp_backfill.py
.venv/bin/python scripts/wp_backfill.py --purge       # rebuild from scratch
```

`--purge` deletes every `bod_issue`/`bod_story`/`bod_release` first; without it each
week is replaced in place, so re-running is safe and resumable.

Weekly publishing to the mirror lives in the maki repo:

```bash
python -m maki_newsletter.wp_sync            # newest week
```

**Two renderers, one markup.** `templates/*.html` (Jinja) and `wordpress/bowlofdata-child/inc/render.php` (PHP) emit the same HTML.

**The theme owns its sitemap.** `/sitemap.xml` on the mirror is generated by `bod_sitemap_xml()` in `inc/seo.php`, not by Yoast, and is built from the same helpers the templates render from (`bod_public_tech_terms()`, `bod_all_issues()`, …) — so it cannot list a URL that has no page. Yoast's own sitemaps are switched off; it is left installed but emits nothing at all. Check the two sides agree after any deploy:

```bash
python3 scripts/check_mirror_parity.py --check-status
```

It diffs the mirror's sitemap against `site/sitemap.xml` and exits non-zero when they disagree — extra paths on the mirror mean it is advertising pages that 404, missing ones mean the weekly `wp_sync` did not land. `build.py` runs the local half of the same check on every build.

> ⚠️ `wordpress/tests/parity.sh` and `wordpress/tests/render_js.mjs` still diff PHP against the retired `netlify/functions/_shared/render.mjs`, which no longer exists. The parity harness needs porting to render its fixture through Jinja instead. Recover the old JS renderer from git history (`git show d031fe4:netlify/functions/_shared/render.mjs`) if you need it as a reference.

Likewise `maki_newsletter/taxonomy.py` duplicates this repo's beat classification, guarded by `tests/test_wp_taxonomy_parity.py` in the maki repo.

---

## Project structure details

### `build.py`

A single incremental build:

1. **Reconcile** — load `weeks_manifest.json`, then scan `MAKI_OUTPUT_DIR` for `summaries_WW_YYYY.json` (plus `model_releases_*` and `curated_papers_*`). A week is re-parsed when its source files are newer than the manifest records, when it is new, or when its HTML is missing. Weeks the pipeline has rotated away survive in the manifest untouched.
2. **Expand** — a changed week also re-renders its two neighbours so prev/next links stay accurate.
3. **Render** — week pages, then the landing page, archive, marketing pages, topic hubs, tag pages and topics index (these last ones are regenerated on every run).
4. **Emit** — `sitemap.xml`, `llms.txt`, `feed.xml`, `robots.txt`.
5. **Persist** — write the manifest back.

`FORCE_REBUILD=1` re-renders every week in the manifest. It does **not** discard the manifest: the maki output directory no longer holds old issues, so that would drop them from the archive permanently.

Classification (`_classify_article`) assigns each item to a beat using the pipeline's `is_governance` flag when present, otherwise a weighted keyword match over `technologies` → `title` → `main_topic`.

### Templates

| Template | Extends | Purpose |
|---|---|---|
| `base.html` | — | Sticky header, footer, Google Fonts |
| `index.html` | `base.html` | Hero, latest-issue card, register |
| `week.html` | `base.html` | One issue |
| `collection.html` | `base.html` | Topic hubs and tag pages |
| `archive.html` | `base.html` | All issues by year → month |

### CSS (`static/style.css`)

Design tokens are defined as CSS custom properties at `:root`. Key palette:

| Variable | Value | Used for |
|---|---|---|
| `--yellow` | `#F5C518` | Accents, header underline, card hover stripe |
| `--yellow-dark` | `#D97706` | Tags, article numbers |
| `--orange` | `#E8613A` | Gradient accents |
| `--gov` | `#6C63C4` | Data & AI Governance beat |
| `--tldr-border` | `#c47f00` | TL;DR box left border |
| `--dark` | `#111827` | Header, footer, dark backgrounds |

### `netlify.toml`

```toml
[build]
  publish = "site"
```

No build command — `site/` is committed. Security headers (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`) apply to all routes.

---

## Data source

Each newsletter issue is driven by a `summaries_WW_YYYY.json` file from the maki pipeline. Relevant fields used by the website:

| Field | Used for |
|---|---|
| `title` | Article heading |
| `url` | External link |
| `source` | Source badge |
| `short_summary` | TL;DR box (2 sentences) |
| `long_resume` | Extended summary paragraphs |
| `main_topic` | Italic topic line |
| `technologies` | Tag pills |
| `quality_score` | Score badge (green ≥ 8, amber otherwise) |
| `is_governance` | Routes the item to the governance beat (optional) |
