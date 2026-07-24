[![Netlify Status](https://api.netlify.com/api/v1/badges/5b9d0b22-a375-46b3-897f-2d4951929886/deploy-status)](https://app.netlify.com/projects/bowofdata/deploys)
[![Substack](https://img.shields.io/badge/Substack-bowlofdata-orange?logo=substack&logoColor=white)](https://substack.com/@bowlofdata)
# Bowl of Data — Website

Website for the [Bowl of Data](https://bowlofdata.net) tech newsletter. **Postgres-backed hybrid site** — low-churn pages are pre-rendered from Jinja2; the content pages that used to explode into hundreds of files (weeks, tags, topics, archive) are now served on request by JavaScript Netlify Functions from a Neon Postgres database.

## Overview

Newsletter content lives in **Postgres** (Netlify DB, powered by Neon) — the single source of truth. The data flows in two directions:

- **Ingestion (local):** `python3 build.py --load` reads the `summaries_WW_YYYY.json` files produced by the [maki](https://github.com/bowlofdata/maki) pipeline and upserts them into Postgres (weeks, items, releases, tags).
- **Static render (Netlify build):** `python3 build.py --render` reads Postgres back and renders the handful of low-churn pages (`index`, `topics`, `about`, `team`, `contact`, `services`) plus `sitemap.xml` / `feed.xml` / `llms.txt` / `robots.txt` into `site/`.
- **Dynamic pages (runtime):** Netlify Functions (`netlify/functions/*.mjs`) query Postgres and server-render full HTML — same markup and SEO (JSON-LD, OG, canonical) as before — for `/week/*`, `/topic/*`, `/tag/*`, and `/archive.html`, cached at the edge.

Nothing generated is committed: `site/` is git-ignored and regenerated on every deploy. The maki pipeline lives in the separate `maki` repo.

---

## Pages

| URL | Served by | Description |
|---|---|---|
| `index.html`, `topics.html`, `about/team/contact/services.html` | **static** (`build.py --render`) | Landing, topics index, and marketing pages |
| `week/WW_YYYY.html` | **function** `week.mjs` | Full issue — article cards, TL;DR, releases, papers, prev/next nav |
| `topic/<slug>.html` | **function** `topic.mjs` | One of the four beats (ai / security / blockchain / engineering) |
| `tag/<slug>.html` | **function** `tag.mjs` | Every item tagged with a technology (≥ 3 items) |
| `archive.html` | **function** `archive.mjs` | Index of all issues, grouped year → month |

---

## First-time setup

**Prerequisites:** Python 3.10+, Node 18+, the [Netlify CLI](https://docs.netlify.com/cli/get-started/), and the `maki` repo cloned as a sibling directory (`../maki/`).

```bash
# 1. Provision the Neon Postgres database (one time). This links the repo to a
#    Netlify DB and injects NETLIFY_DATABASE_URL into build + function runtimes.
netlify db init

# 2. Apply the schema
psql "$NETLIFY_DATABASE_URL" -f scripts/schema.sql

# 3. Python + Node deps
pip install -r requirements.txt
npm install

# 4. For the local --load step, put the connection string in a .env file (git-ignored):
echo "NETLIFY_DATABASE_URL=postgres://…" > .env
```

Preview the whole site locally (static pages + functions + redirects) with:

```bash
netlify dev      # serves /week/*, /tag/*, /topic/*, /archive.html from Postgres
```

The loader looks for newsletter data in `../maki/maki_newsletter/output/` by default; override with `MAKI_OUTPUT_DIR=/path/... python3 build.py --load`.

---

## Full weekly workflow

```bash
# 1. Run the maki pipeline (in the maki repo) → summaries_WW_YYYY.json
python -m maki_newsletter.main
python -m maki_newsletter.generate

# 2. Load the new issue into Postgres (in this repo)
python3 build.py --load

# 3. Deploy — no generated files to commit
git commit -am "newsletter week WW YYYY"   # only source/code changes, if any
git push
# Netlify runs `build.py --render` (Postgres → static pages) and deploys the
# functions. New week/tag/topic content appears immediately, served from Postgres.
```

Because the data lives in Postgres, a new issue often needs **no repo change at all** — `build.py --load` publishes it. Push only when you also change code/templates, or trigger a redeploy from the Netlify UI to refresh the cached static pages and edge cache.

---

## Project structure details

### `build.py` — two modes

- **`--load`** — scans `MAKI_OUTPUT_DIR` for `summaries_WW_YYYY.json` (plus `model_releases_*` and `curated_papers_*`), normalises and classifies each item (reusing `_classify_article`, `_slugify`, `_normalise_*`), and **upserts** into Postgres. Each week is replaced atomically (`weeks` upsert + delete/re-insert of that week's `items`/`releases`/`item_tags`), so re-running is idempotent. Removing a source file does **not** delete the week from Postgres.
- **`--render`** — reads every week back from Postgres and renders the static surface (`index`, `topics`, `about`, `team`, `contact`, `services`) plus `sitemap.xml` / `feed.xml` / `llms.txt` / `robots.txt`. This is the Netlify build command.

### `netlify/functions/` — dynamic pages (JS)

Server-render full HTML from Postgres via the `@netlify/neon` driver. `_shared/render.mjs` mirrors the Jinja templates so the output markup and JSON-LD are byte-identical to the static build; `_shared/db.mjs` holds the connection + cache headers; `_shared/topics.mjs` holds the beat metadata.

| Function | Route (via `netlify.toml` rewrites) |
|---|---|
| `week.mjs` | `/week/*` |
| `topic.mjs` | `/topic/*` |
| `tag.mjs` | `/tag/*` |
| `archive.mjs` | `/archive.html` |

> **Two shells to keep in sync:** the page shell (header/footer/nav) exists in `templates/base.html` (static pages) **and** `render.mjs` `shell()` (dynamic pages). Change both together — a function page and its Jinja counterpart should differ only in whitespace.

### Database (`scripts/schema.sql`)

`weeks`, `items` (articles + papers), `releases`, and `item_tags` (one row per item×technology). Topics are derived from `items.category`; tag pages from `item_tags`. See the file for the full DDL.

### Templates

| Template | Extends | Purpose |
|---|---|---|
| `base.html` | — | Sticky header, footer, Google Fonts (static pages) |
| `index.html` | `base.html` | Hero, latest-issue card, register |
| `week.html` / `collection.html` / `archive.html` | `base.html` | Reference markup the JS functions mirror |

### CSS (`static/style.css`)

Design tokens are defined as CSS custom properties at `:root`. Key palette:

| Variable | Value | Used for |
|---|---|---|
| `--yellow` | `#F5C518` | Accents, header underline, card hover stripe |
| `--yellow-dark` | `#D97706` | Tags, article numbers |
| `--orange` | `#E8613A` | Gradient accents |
| `--tldr-border` | `#c47f00` | TL;DR box left border |
| `--dark` | `#111827` | Header, footer, dark backgrounds |

### `netlify.toml`

```toml
[build]
  command = "pip install -r requirements.txt && python3 build.py --render"
  publish = "site"
```

The build renders the static pages from Postgres; `[[redirects]]` rewrite (status `200`) `/week/*`, `/topic/*`, `/tag/*`, and `/archive.html` to the functions so the **public URLs are unchanged**. Security headers (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`) apply to all routes.

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
