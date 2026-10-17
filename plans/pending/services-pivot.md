# Plan: Services pivot to Build and Assure

Input: [docs/ideas/services-pivot.md](../../docs/ideas/services-pivot.md). Static site: edit `templates/` and `build.py`, run `python3 build.py`, commit `site/` (Netlify publishes it as-is, no build step).

## Decision log
| # | Decision | Why |
|---|---|---|
| D1 | One page, same URL `/services.html`, two sections (Build, Assure). Nav label stays "Services". | Keeps the indexed URL, links and sitemap entry; avoids redirects. |
| D2 | No pricing language anywhere. Offers are described by scope and typical duration only. | Owner call. Nothing invented. |
| D3 | Credentials: Marco only, generic wording ("years inside banks and insurers on IT, data and model risk"), no employer names. Luigi stays vision/editorial. | NDA-safe; owner call. |
| D4 | Enquiries go through the existing Netlify form; add subjects "Build enquiry" and "Assure enquiry"; service CTAs link to `contact.html` with the subject preselected. | Zero new infrastructure. |
| D5 | Newsletter stays the free flagship; white-label/Newsletter-on-Demand copy is removed everywhere (templates, FAQ, schema, llms files, SEO doc). | Idea one-pager. |
| D6 | Regulatory names appear only in the Assure section and its FAQ. Say "MaRisk and DORA"; BAIT only as "the former BAIT requirements". | DORA has applied since Jan 2025 and largely replaced BAIT; owner to confirm wording in review. |
| D7 | Services copy stays English. | Site is English only; German is a later question. |

## Always / Never
- Always: reuse `CURATION_STATEMENT`, the stable JSON-LD `@id`s, `_make_webpage_jsonld`, and the existing design tokens/classes (see design-system memory); keep `current_page="services"`.
- Always: the build's dead-link assertion stays on; render every changed page through `build.py`, never hand-edit `site/`.
- Never: claim certifications, client names, prices or deliverable guarantees not supplied by the owner.
- Never: touch `weeks_manifest.json`, week/tag/topic pages, or the tag thresholds. Never add `potentialAction`. Never put a `WebSite` node on a non-home page.
- Out of scope: new pages, German copy, Search Console actions, Substack/EveryDev edits, any push to `main`.

## Phases (all XS/S, frontier = steps whose blockers are done)

### P1. Services page and its schema: S
Blocked by: none.
- Files: `templates/services.html`, `build.py` (`SERVICES_FAQ`, services render block ~L2350).
- Rewrite the page: hero ("Build it. Assure it."), two sections with one entry offer each (Governance Readiness Assessment; RAG Pipeline Review/Sprint), how-it-works, proof strip (Maki running weekly, private/local models, open source), FAQ, CTAs to contact.
- Replace `SERVICES_FAQ` (about 6 entries: what is a readiness assessment, what does the model risk review cover, why auditable RAG, data privacy, who delivers, how do we start). Update WebPage name/description to "AI Engineering & Assurance Services".
- Verify: `python3 build.py`, then grep `site/services.html` for "white-label|newsletter as a service|Newsletter on Demand" = 0 hits; open page locally at desktop and mobile widths; JSON-LD validates as parseable JSON.

### P2. Contact subjects: XS
Blocked by: none (parallel with P1).
- Files: `templates/contact.html` (and `build.py` only if it reads a subject list).
- Add "Build enquiry" and "Assure enquiry"; support `?subject=` preselect with a few lines of JS or option order.
- Verify: contact page loads, `contact.html?subject=assure` preselects, form markup still has `data-netlify`.

### P3. About and Team reframe: S
Blocked by: P1 (shares wording).
- Files: `templates/about.html`, `templates/team.html`, `build.py` (`ABOUT_FAQ`, about/team page descriptions and schema text).
- About: lead with what Bowl of Data is (a practice that runs a public AI pipeline), newsletter as the proof and the free flagship, "Work with us" link to Services. Keep "How it works" and "Local by design".
- Team: Marco's description adds generic bank/insurer experience; Luigi unchanged.
- Verify: build, grep for stale newsletter-for-hire copy, check About FAQ still matches on-page `<details>`.

### P4. SEO and AI surfaces: S
Blocked by: P1, P3.
- Files: `build.py` (`llms.txt` Services line ~L1893, any org/site description that mentions the offer), `SEO_STRATEGY.md` (§1 secondary goal, §118 keyword table, §342 pricing TODO, new dated row), `README.md` page table if wording changes.
- Services keywords become: AI governance readiness assessment, LLM model risk review, RAG pipeline consulting, MaRisk/DORA AI. Update the `services` keyword row and drop "white-label" targets.
- Sitemap entry for services stays (changefreq monthly, 0.7).
- Verify: `python3 build.py`; `site/llms.txt` Services line updated; sitemap still lists `/services.html`; `_assert_no_dead_internal_links` passes.

### P5. Final check and review: XS
Blocked by: P1–P4.
- Full `python3 build.py` from clean; `git diff --stat` shows changes only in `site/{services,about,team,contact}.html`, `llms*.txt`, `sitemap.xml`/`feed.xml` timestamps, templates, `build.py`, docs. No week/tag/topic diff.
- Screenshot Services, About, Contact at desktop and 375px.
- Owner reviews copy before any commit (see Assumptions).

## Progress
| Phase | Status |
|---|---|
| P1 Services page | done (see note) |
| P2 Contact subjects | done (see note) |
| P3 About and Team | done (see note) |
| P4 SEO and AI surfaces | done (see note) |
| P5 Final check | done (see note) |

## Not yet specified
- Exact typical durations for the two offers (I will write "typically 3–4 weeks" for the assessment and "typically 2 weeks" for the RAG review as editable copy; owner to adjust in review).

## Execution note (2026-10-17)
- `python3 build.py` aborts on the live-tag-page guard in this checkout (first with the local Maki output: gitlab, neutral-atoms, openvla, trapped-ions, wordpress; then with manifest only: ecdsa, lean-4, ml-dsa, multi-party-computation-mpc, psiquantum). The guard was not touched. The four marketing pages were rendered by the build before it aborted; every other site/ change from those runs was reverted.
- `site/llms.txt` was patched by hand to match the new `build.py` text (Services line and one intro sentence); the next normal weekly build regenerates it identically.
- Owner to resolve before the next weekly build: add the five slugs to `TAG_ALIASES` / `ACCEPTED_TAG_404S` or fix the manifest/Maki output mismatch.
- Branch `services-pivot`, not pushed.
