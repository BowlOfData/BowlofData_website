[![Netlify Status](https://api.netlify.com/api/v1/badges/5b9d0b22-a375-46b3-897f-2d4951929886/deploy-status)](https://app.netlify.com/projects/bowofdata/deploys)
# Bowl of Data — Website

Static website for the [Bowl of Data](https://bowlofdata.netlify.app) tech newsletter. Built with Jinja2 templates and deployed on Netlify.

## Overview

The site is a **pre-built static site**: `build.py` reads newsletter data produced by the [maki](https://github.com/bowlofdata/maki) pipeline, renders HTML via Jinja2 templates, and writes the output to `site/`. The `site/` directory is committed to the repo and served by Netlify as-is — no server-side processing, no build step on Netlify.

```
BowlofData_website/
├── build.py              # Site generator (run locally after each newsletter)
├── weeks_manifest.json   # Incremental build state — commit this to git
├── requirements.txt      # Python deps (jinja2, python-dotenv)
├── netlify.toml          # Netlify config — publishes site/
├── imgs/                 # Brand assets (logo.png)
├── static/               # CSS source
│   └── style.css
├── templates/            # Jinja2 HTML templates
│   ├── base.html         # Shared header, footer, fonts
│   ├── index.html        # Landing page + archive grid
│   └── week.html         # Individual newsletter issue
└── site/                 # Generated output (committed, served by Netlify)
    ├── index.html
    ├── imgs/
    ├── static/
    └── week/
        └── WW_YYYY.html
```

The newsletter pipeline lives in the separate `maki` repo (`maki_newsletter/`). This repo only contains the website frontend and the build script.

---

## Pages

| Page | Description |
|---|---|
| `index.html` | Landing page with a "Latest Issue" preview card and a full archive grid |
| `week/WW_YYYY.html` | Full newsletter issue — article cards with TL;DR, extended summary, tags, and prev/next navigation |

---

## Local setup

**Prerequisites:** Python 3.10+, and the `maki` repo cloned as a sibling directory (`../maki/`).

```bash
# Install dependencies
pip install -r requirements.txt

# Build the site
python3 build.py
```

The builder looks for newsletter data in `../maki/maki_newsletter/output/` by default.
To use a different path:

```bash
MAKI_OUTPUT_DIR=/path/to/maki_newsletter/output python3 build.py
```

Open `site/index.html` in a browser to preview.

---

## Full weekly workflow

After running the maki newsletter pipeline:

```bash
# 1. Run the maki pipeline (in the maki repo)
python -m maki_newsletter.main       # fetch, analyse, rank articles
# review and edit output/summaries_WW_YYYY.json if needed
python -m maki_newsletter.generate   # write the newsletter markdown
python -m maki_newsletter.publish    # publish to Altervista (optional)

# 2. Rebuild the website (in this repo)
python3 build.py

# 3. Deploy
git add site/
git commit -m "newsletter week WW YYYY"
git push
# Netlify picks up the push and deploys automatically
```

---

## Project structure details

### `build.py`

Scans `MAKI_OUTPUT_DIR` for `summaries_WW_YYYY.json` files, normalises each article dict (strips internal fields like `local_path`), and renders:
- one `site/week/WW_YYYY.html` per week
- one `site/index.html` listing all weeks

Each week page receives `prev_week` / `next_week` context for issue-to-issue navigation.

**Incremental build** — the builder runs in four phases:

1. **Reconcile** — compare each source JSON's mtime against `weeks_manifest.json`. Only new or changed files are queued for rendering.
2. **Expand** — also queue the immediate neighbours (older and newer issue) of any changed week, so their prev/next navigation links stay accurate.
3. **Render** — write HTML only for queued weeks; all other existing pages are untouched.
4. **Persist** — update `weeks_manifest.json` with the current build state.

**Deletion safety** — when a `summaries_WW_YYYY.json` is removed from the maki output directory, its entry remains in `weeks_manifest.json` and its built HTML is preserved. The archive index is always derived from the manifest, not from what source files currently exist on disk.

**Force a full rebuild:**
```bash
FORCE_REBUILD=1 python3 build.py
```

### Templates

| Template | Extends | Purpose |
|---|---|---|
| `base.html` | — | Sticky header, footer, Google Fonts |
| `index.html` | `base.html` | Hero, latest-issue card, archive grid |
| `week.html` | `base.html` | Article list with TL;DR boxes, long resumes, nav |

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
  publish = "site"
```

No build command — Netlify serves the pre-built `site/` directory directly. Security headers (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`) are applied to all routes.

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
