# Bowl of Data — SEO, GEO & Growth Strategy

_Last updated: 2026-08-12. Owner: Marco. Companion to the code changes shipped in
`build.py` and the `templates/`. This is the "why and what next" — the code is the "how"._

> **2026-08-12 — the domain question is settled.** `bowlofdata.net` now resolves to Netlify
> and serves real deep paths. The Altervista WordPress mirror, which existed only because
> the domain previously could not, has been **retired to a blanket 301**. Until that
> happened, two sites published identical titles and identical sitemaps at identical paths
> and split the authority for every query — the single largest loss on the site, larger
> than anything on-page. §4 below is rewritten around one canonical domain.

---

## 1. Positioning

**One line:** Bowl of Data is the *source of record* for the week in technology — AI,
cybersecurity, blockchain, and software engineering — curated by an AI pipeline (Maki) and
reviewed by humans, shipped every Saturday.

**Primary goal:** grow the free Substack subscriber base. **Secondary:** make the
"Newsletter on Demand" services page rank for commercial intent.

**Canonical home:** `bowlofdata.net`. The full issue lives here; Substack is the email push.
Every SEO decision assumes `.net` is the thing we want ranked.

Why this matters: the broad head terms ("AI newsletter", "tech newsletter") are owned by
TLDR, Morning Brew, and Bench. We do **not** win those by frontal assault. We win the
**long tail** (specific technologies, CVEs, model releases, "this week in X") and we win
**AI answer engines**, where being a clean, current, well-structured source beats domain
authority.

---

## 2. What shipped (on-page + technical)

| Area | Change | Where |
|---|---|---|
| Topic hubs | 5 beat landing pages aggregating every issue | `site/topic/{ai,governance,security,blockchain,engineering}.html` |
| Tag pages | 120 auto-generated technology pages (≥3 items each) | `site/tag/<slug>.html` |
| Topics index | Hub-of-hubs for internal linking + discovery | `site/topics.html` |
| Structured data | NewsArticle w/ publisher+author+image; BreadcrumbList; FAQPage; CollectionPage | `build.py` JSON-LD helpers |
| — *correction* | **FAQPage earns no rich result.** Google restricted them to government and health sites in 2023. It stays because AI answer engines still parse it, but it is not a ranking win and should not be counted as one | `about.html`, `services.html` |
| Internal linking | Beat cards, article category badges, clickable tag chips all link into hubs/tags | `index.html`, `week.html`, `topics.html` |
| GEO | `llms.txt` Topics/Tags sections + "source of record" line; E-E-A-T authorship line; freshness dates | `build.py`, `base.html` |
| Conversion | Reusable subscribe CTA on every week/hub/tag page with UTM tags | `templates/_subscribe.html` |
| OG/meta | `og:image` dimensions/alt, `og:type=article`, keyworded titles | `base.html`, `index.html` |
| **Week titles** (2026-08-12) | Dated, keyworded titles + unique meta descriptions per issue — they were all `Week NN · YYYY` with one shared description | `build.py` `_week_coverage_range`, `week.html` |
| **Social titles** (2026-08-12) | `og_title` block so share cards drop the redundant `· Bowl of Data` suffix | `base.html`, `week.html` |
| **Outbound links** (2026-08-12) | Article/release headlines are plain text; the source link lives in the card footer. Cut a week page from 75 off-site links to 41 | `week.html` |
| **Schema honesty** (2026-08-12) | `NewsArticle.url` points at our own anchor with `isBasedOn`/`citation` for the source, instead of claiming the publisher's article as ours | `build.py` `_make_week_jsonld` |
| **Commercial page** (2026-08-12) | `services.html` rewritten around "newsletter as a service", "white-label", "agency"; 5 new FAQ entries | `templates/services.html`, `SERVICES_FAQ` |
| **404** (2026-08-12) | Branded 404 with absolute asset paths, linking back into archive/topics | `templates/404.html` |

**Anti-duplication rule (keep this):** hub and tag pages show a title + short summary + a link
to the canonical week-page anchor. They must **never** render the full `long_resume` — that
text lives only on the issue page. Duplicating it would split our own authority.

---

## 3. Keyword & entity map

Rank targets by page. Treat these as the queries each page should plausibly earn — check
reality in Search Console after 4–8 weeks and adjust.

| Page | Primary | Long-tail / secondary |
|---|---|---|
| Landing | bowl of data; weekly tech newsletter | AI security newsletter; weekly tech digest |
| `topic/ai` | AI newsletter; this week in AI | weekly AI model releases; AI research digest |
| `topic/governance` | AI governance newsletter | EU AI Act updates; AI regulation this week |
| `topic/security` | cybersecurity newsletter | weekly CVE roundup; this week in security |
| `topic/blockchain` | crypto newsletter | weekly blockchain news; stablecoin news |
| `topic/engineering` | software engineering newsletter | open-source releases this week |
| `tag/<x>` | "\<tech\> news weekly" | "\<tech\> \<recent event\>" (bitcoin, ethereum, quantum computing, llms, npm…) |
| `services` | newsletter as a service; done-for-you newsletter | AI newsletter agency; white-label newsletter |

The tag pages are the volume play: 120 of them, each a small, focused net for a long-tail
query. They cost nothing extra per issue — new tags appear automatically once a technology
hits 3 items.

**The volume play needs a quality gate, and it now has one — switched off.** As of
2026-08-12, 70 of 105 tag pages held only 3–4 items, many of them one-off entities the
classifier minted rather than durable technologies (`anthropic-mythos`, `claude-mythos-5`,
`focil`). `topic/governance.html` is thinner still, at 4 items across the whole archive.
`MIN_INDEXABLE_ITEMS` in `build.py` adds `noindex,follow` and drops a page from the sitemap
below a threshold, **and ships at `0` so nothing is pruned yet** — pruning before Search
Console has impression data for those URLs would be guessing, and §8 already says to decide
on data. Expect roughly 131 → 85 sitemap URLs on a first cut at the 3-item tier plus
`governance`; that drop is the plan working, not a catastrophe.

> **Never conflate the two thresholds.** `_collect_tags(min_items=3)` decides whether a
> page **exists** — raising it deletes files and 404s URLs Google already knows.
> `MIN_INDEXABLE_ITEMS` decides whether it is **indexed**, leaving the page reachable and
> still passing link equity. Only ever move the second one.

---

## 4. Canonical policy (important — do not skip)

**There is exactly one canonical site: `https://bowlofdata.net` (apex, no `www`).**

1. **`.net` pages are canonical.** Enforced via `<link rel="canonical">` on every page.
2. **On Substack, set each post's canonical URL to the matching `.net` page.** Substack
   supports this per-post (Settings → SEO → Canonical URL). Do it every issue, or Google may
   rank the Substack copy and we lose the on-site funnel.
3. Never publish a tag/hub page's aggregated text as a standalone Substack post — it would
   duplicate the issue pages.
4. **The Altervista mirror is retired** and 301s to `.net`. Do not revive it as a live site;
   see the README's WordPress section.
5. **`bowofdata.netlify.app` still answers 200** and is the last remaining duplicate host.
   Close it by setting the **apex** as the primary domain in Netlify → Site configuration →
   Domain management, which auto-301s the subdomain. Choosing `www` as primary would invert
   the existing `www` → apex redirect and invalidate every canonical on the site.

**Two things not to "fix":**

- **Do not disable Netlify's Pretty URLs** to resolve `/about` vs `/about.html` both
  answering 200. If any extensionless URL is indexed, disabling it converts live URLs into
  hard 404s — trading a duplicate that canonicals already resolve for real link rot.
- **Do not disable Netlify post-processing wholesale.** Netlify Forms registration is part
  of it, and `site/contact.html` depends on `data-netlify="true"`. After any change in that
  settings panel, confirm the `contact` form still appears under Netlify → Forms.

---

## 5. GEO playbook (be the source AI engines cite)

A rising share of "visibility" is a citation inside ChatGPT / Perplexity / Google AI
Overviews, not a blue-link click. We're well-placed; keep it that way:

- **Keep `llms.txt` current** — it now lists issues, topics, and tags with a positioning
  line. It regenerates on every build.
- **Entity-first summaries.** Each TL;DR should name the entity + the fact in sentence one
  ("OpenAI released X, which…"). This is what engines lift verbatim.
- **Freshness signals.** `dateModified`/`datePublished` ship in the schema; the weekly cadence
  is our advantage — engines prefer the current source.
- **Authorship/E-E-A-T.** The footer now states human review; the About page explains the
  pipeline. Keep the "reviewed by humans" claim true and visible.
- **Spot-check monthly:** ask ChatGPT and Perplexity "what happened this week in \<topic\>"
  and see whether Bowl of Data is cited. Track it like a keyword.

---

## 6. Off-page & distribution (the real subscriber driver)

On-page gets us *eligible* to rank; links and distribution get us *ranked* and *read*.
Priority order:

1. **Newsletter directories** (fast backlinks + discovery): submit to InboxReads,
   newsletter.directory, The Sample, Refind, Feedspot tech lists. One afternoon of work.
2. **Community seeding**, when an issue has a genuinely strong lead item: post the *source*
   discussion to Hacker News, r/programming, r/netsec, Lobste.rs — not spammy self-promo, but
   the story. Link back where natural.
3. **Backlink outreach:** when we summarize a company/researcher's work favorably, tell them.
   Many will link or share. This compounds.
4. **Podcast SEO:** ensure the Spotify show has a keyword-rich description and links to `.net`;
   submit the RSS to Apple/Google/Overcast for more surfaces.
5. **Cadence flywheel:** every Saturday issue is fresh crawlable content + a social/Substack
   moment + a reason for a return visit. Consistency is the moat — never miss a week.

---

## 7. Conversion (subscribers first)

Traffic that doesn't convert is wasted. Shipped: a repeated subscribe CTA on every
week/hub/tag page, UTM-tagged so it's measurable. Next levers, in order of ROI:

- **Track the subscribe click** as the primary conversion event. UTM `campaign` distinguishes
  `week` / `topic` / `tag` / `topics` / `inline`.

  > **Fixed 2026-08-12 — mind the discontinuity.** `collection.html` hardcoded
  > `subscribe_ctx = 'topic'`, and it renders both the hubs and the tag pages, so until this
  > date **all 120 tag pages reported `utm_campaign=topic`** and were indistinguishable from
  > the 5 hubs. Substack acquisition data before and after this date is not comparable for
  > those two labels. This also had to be fixed before §8's tag pruning could be decided on
  > evidence — impressions alone don't show which thin pages actually earn subscribers.
- **Lead-magnet test:** try "the best of the month" or a themed back-issue as an incentive.
- **Later:** an embedded email field (Substack embed) to cut the click-out friction, and
  simple A/B on CTA copy.

---

## 8. Measurement — monthly review loop

1. **Search Console:** top queries, impressions, CTR, and which hub/tag pages get indexed and
   earn clicks. Kill or merge tag pages that never get impressions after 3 months.
2. **Subscribe rate:** conversions / sessions from the UTM'd CTAs.
3. **GEO check:** the ChatGPT/Perplexity citation spot-check from §5.
4. **Indexing hygiene:** after each deploy, confirm the sitemap submitted cleanly and request
   indexing for any important new hub/tag pages.

---

## 9. Checklist

**Shipped 2026-08-12** — dated week titles + unique descriptions, `og_title` decoupling,
headlines unlinked, JSON-LD attribution, `MIN_INDEXABLE_ITEMS` (inert), tag UTM fix,
services page rewrite, branded 404, image dimensions + `marco.jpg` 566 KB → 109 KB,
`/imgs/*` cache header, WordPress mirror retired to a 301.

**Owner actions, blocking:**

- [ ] Deploy the WordPress theme (`build_wp_theme.py` then `deploy_wp_theme.py`), then run
      `python3 scripts/check_mirror_parity.py` — it asserts the 301s and that robots.txt
      still answers 200.
- [ ] Set the **apex** as primary domain in Netlify to close `bowofdata.netlify.app`.
- [ ] Submit `sitemap.xml` in Search Console; request indexing for `topics.html` + the hubs.
- [ ] Add `bowlofdata.altervista.org` as a Search Console property and watch its impressions
      decay to zero — that is the consolidation working.
- [ ] Set canonical URLs on recent Substack posts to their `.net` equivalents; per-issue habit.

**Then, in order:**

- [ ] Decide on pricing for `services.html`. The page now answers "what does it cost?" with
      "a flat monthly fee, scoped to you" — a real number, or even a "from $X", converts
      better and unlocks pricing-shaped queries. Nothing was invented here on purpose.
- [ ] Submit to 4–5 newsletter directories.
- [ ] Run the GEO spot-check and record a baseline.
- [ ] After 4–8 weeks of Search Console data: raise `MIN_INDEXABLE_ITEMS` per §3.
- [ ] Look at `Week 21 · 2026` (51 articles) and `Week 33 · 2026` (42) — every other issue
      holds 11–20. Likely predates the `fix duplicates` work.
