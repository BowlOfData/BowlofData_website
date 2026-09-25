# Bowl of Data — SEO, GEO & Growth Strategy

_Last updated: 2026-09-02. Owner: Marco. Companion to the code changes shipped in
`build.py` and the `templates/`. This is the "why and what next" — the code is the "how"._

> **2026-08-12 — the domain question is settled.** `bowlofdata.net` now resolves to Netlify
> and serves real deep paths. The Altervista WordPress mirror, which existed only because
> the domain previously could not, was **written up as retired to a blanket 301**. Until that
> happened, two sites published identical titles and identical sitemaps at identical paths
> and split the authority for every query — the single largest loss on the site, larger
> than anything on-page. §4 below is rewritten around one canonical domain.
>
> **2026-09-02 — the retirement is now DEPLOYED and verified live.** Every front-end path on
> `bowlofdata.altervista.org` 301s single-hop to its `.net` twin (25/25 sampled by
> `check_mirror_parity.py`), `robots.txt` still answers 200 so crawlers can still reach the
> 301s, and `/feed/` lands on `https://bowlofdata.net/feed.xml`. What follows is the state
> found immediately before that deploy, kept because it explains the symptom and the lesson.
>
> **The retirement had been written up as shipped since 2026-08-12 but never deployed.** Verified
> live: `bowlofdata.altervista.org/` answers **200**, self-canonicalises to
> `https://bowlofdata.altervista.org/`, and serves its own 144-URL `sitemap.xml` with
> `robots.txt: Disallow:` (allow all). The theme running there is *older* than the code in
> `wordpress/` — the repo's `BOD_CANONICAL_ORIGIN` is already `bowlofdata.net`, so the live
> install predates even the 2026-08-12 canonical change. The split described above is not
> historical; it is happening right now, and it is why the query `bowlofdata` returns the
> Altervista copy while `bowl of data` returns `.net`. **The single largest loss on the site
> remains open.** See §9's first blocking action.

---

> **2026-09-06 — the Substack is not a duplicate-content problem, verified.** Worth stating
> because the Altervista split (§4) was exactly this failure mode and the suspicion is a
> natural one. Fetched live: `bowlofdata.substack.com/p/bowl-of-data-week-36-2026` is a
> **teaser**, not a copy — a headline and 2-3 sentences per story — and it links to
> `bowlofdata.net/week/36_2026.html` six times, after each story and again under "Full
> issue". The full `long_resume` text exists only on `.net`. The email push and the canonical
> home are correctly split, and nothing needs fixing here. Do not "add a canonical" to the
> Substack on the strength of the resemblance to the mirror problem — there is no duplication
> to resolve, and the six per-issue backlinks are an asset.

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
| Topic hubs | 7 beat landing pages aggregating every issue | `site/topic/{ai,governance,security,blockchain,engineering,quantum,space}.html` |
| Tag pages | 140 auto-generated technology pages (≥3 items each) | `site/tag/<slug>.html` |
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
| **Tag cross-links** (2026-09-02) | Every tag page now links to the 10 tags it most often shares an item with. Tag pages were leaf nodes: 129 pages with inbound links and *zero* outbound links to each other. Median inbound links per tag page 9 → 10, and the long tail is now a connected cluster instead of 140 dead ends | `build.py` `_collect_tags` co-occurrence, `collection.html` |
| **Dead internal links** (2026-09-02) | 16 dead `../tag/*.html` links across five issues, from skipped week pages whose chips pointed at slugs the classifier had since renamed. Fixed by re-rendering any week whose on-disk chips go stale, and asserted at build time | `build.py` `_assert_no_dead_internal_links` |
| **Aggregation snippets** (2026-09-02) | Hub and tag meta descriptions were a bare item count. They now carry issue span **and recency** (`… 44 stories across 14 issues, latest 29 August 2026`), trimmed to 155 chars — recency is the one thing these pages have that a static page does not | `build.py` `_collection_freshness`, `_fit_meta` |
| **`article:*` OG tags** (2026-09-02) | Week pages declared `og:type=article` with no `published_time`/`modified_time`, leaving scrapers and answer engines to guess at freshness. Now stamped, plus `article:section` and the issue's 8 most-repeated technologies as `article:tag` | `base.html` `og_article_meta`, `week.html`, `_week_og_tags` |
| **Collection `og:type`** (2026-09-02) | Hub and tag pages claimed `og:type=article`. They are indexes of other pages; they now declare `website` | `templates/collection.html` |
| **E-E-A-T attribution** (2026-09-02) | "Reviewed by humans" was an unattributed claim. `Organization.founder` now carries `Person` nodes with the LinkedIn `sameAs` already public on `team.html` — `sameAs` is what resolves a name to a known entity | `build.py` `FOUNDERS`, `_founder_nodes` |
| **Newsletter as an entity** (2026-09-06) | The site's whole purpose is to be the entry point for a newsletter, and no node said a newsletter existed. Added a `Periodical` (`#newsletter`) carrying cadence, free-to-read, genre and `sameAs` the Substack; week pages are now multi-typed `["CollectionPage","PublicationIssue"]` with `issueNumber` + `isPartOf`. 18 unrelated collection pages became 18 issues of one publication | `build.py` `_periodical_node`, `_make_week_jsonld` |
| **Stable `@id`s** (2026-09-06) | Organization, WebSite and Periodical now have `@id`s and every nested node references them instead of restating name/logo/url. The Periodical rides on the organization node emitted by `base.html`, so a tag page reached from a long-tail query resolves to the publication exactly as the homepage does | `build.py` `_make_organization_jsonld`, `_publisher_node` |
| **Archive schema** (2026-09-06) | The archive rendered the same generic `WebSite` node as every other static page. It is the newsletter's issue index, so it now emits a `CollectionPage` listing all issues as `PublicationIssue` nodes keyed by the same `@id` the week pages declare, plus a breadcrumb | `build.py` `_make_archive_jsonld` |
| **Archive keywords** (2026-09-06) | Title/H1/description were `Archive` / "All issues" / a generic sentence — zero newsletter intent on the one page that indexes the whole publication. Now `Newsletter Archive — All 18 Issues` and an H1 to match | `templates/archive.html` |
| **Subscribe CTA on home + archive** (2026-09-06) | The reusable CTA was on every week, hub and tag page but **not** on the two pages most likely to be the entry point. Added with `utm_campaign=home` / `archive` | `templates/index.html`, `templates/archive.html` |
| **`llms.txt` lead** (2026-09-06) | The file described the pipeline before it described the product, and buried the subscribe link under "Optional". It now leads with "free weekly newsletter, one issue every Saturday", names `.net` as the newsletter's home, and states the subscribe URL in prose an answer engine can quote | `build.py` `_generate_llms_txt` |
| **Page types** (2026-09-06) | `about`, `contact`, `team`, `services` and `404` all rendered the generic `WebSite` node from `shared` — five pages each claiming to *be* the whole site. Now `AboutPage` / `ContactPage` / `AboutPage` / `WebPage` / none, each `isPartOf` the one `#website` and `about` the org and/or the newsletter. Only the homepage is a `WebSite` now | `build.py` `_make_webpage_jsonld` |
| **Topics index node** (2026-09-06) | It was passing its breadcrumb through the `jsonld_str` slot, leaving it the only content page with nothing describing the page itself. Now a `CollectionPage`, breadcrumb moved to its own slot | `build.py` topics render |
| **Static-page breadcrumbs** (2026-09-06) | `about`, `team`, `contact`, `services` and `archive` had none; week, hub and tag pages always did | `build.py` |

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

The tag pages are the volume play: 140 of them, each a small, focused net for a long-tail
query. They cost nothing extra per issue — new tags appear automatically once a technology
hits 3 items.

**As of 2026-09-02 they are also a graph, not a pile.** Each tag page links to the ten tags
it most often shares an item with, so `bitcoin` reaches `etf`, `post-quantum-cryptography`
and `stablecoins` directly. This matters more than it looks: a page that nothing links *out
of* is a dead end for crawl depth and passes none of its equity onward, and 129 of them were
exactly that. Only tags that survived `min_items` are eligible as link targets — linking to
a slug that was never rendered would put a 404 inside our own graph, which is precisely the
bug the same pass found and fixed on the week pages.

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
4. **The Altervista mirror is retired**, as of 2026-09-02 and verified in production, not
   just in the repo. `BOD_RETIRED_TO` in `wordpress/bowlofdata-child/functions.php` 301s
   every front-end request to its `.net` twin. Do not revive it as a live site, and do not
   delete the install or free the subdomain — a 301 has to keep answering for months for
   Google to transfer the signals. Re-verify after any WordPress or host change with
   `python3 scripts/check_mirror_parity.py`.
   Two exemptions in that redirect are load-bearing: `is_robots()`, because WordPress serves
   `robots.txt` through the template loader *after* `template_redirect` and a crawler that
   cannot read it never sees the 301s; and `is_feed()`, because the blanket redirect
   preserves the path and `.net` publishes `/feed.xml`, not `/feed/` — without the
   exemption every RSS subscriber is 301'd into a 404.
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

**Shipped 2026-09-25** — tag synonym merge. The classifier spelled one concept many ways
(five separate LLM pages; `ai`/`artificial-intelligence`/`machine-learning` tags competing with
`topic/ai.html`). `TAG_ALIASES` in `build.py` folds each variant into one canonical page,
`TAG_TO_HUB` sends the generic AI/ML/blockchain tags to their hubs, and `site/_redirects` 301s
every retired URL. Tag pages: 164 → 155; `large-language-models-llms` went from 24 to 47
stories. Two guards keep it that way: the build **aborts** if a live tag page would vanish
without a 301 (unless listed in `ACCEPTED_TAG_404S`), and it **prints** likely new synonym
groups each run — fold real ones into `TAG_ALIASES`, silence false ones in `TAG_NOT_SYNONYMS`.
Of the 43 tag URLs that had silently 404'd since the early-August dedupe, the four real
synonyms (`btc`, `ether`, `codex-cli`, `deep-learning`) now 301; the other 39 held 1–2 items
for 1–3 weeks, mostly before `.net` served real paths, and stay 404 on purpose — redirecting
them to a hub would only be a soft 404.
Same pass: **issue meta descriptions now name the week's top technologies** ("…20 curated
stories on Bitcoin, Large Language Models (LLMs), AI Agents and more…") instead of one templated
sentence with only the date and counts changed — all 20 are now distinct and ≤155 chars.
`article:tag` folds synonyms. **Reddit flair (`[P]`/`[R]`/`[D]`) and InfoQ's `Article:` prefix are
stripped from displayed headlines** (h2, JSON-LD, RSS, llms.txt, archive) — display only: the stored
title and its anchor slug are untouched, so Substack's `#anchor` links still resolve.
**Not fixable in the build:** first-person Reddit titles ("my new video on…", "I built…") need
rewriting, which belongs in Maki as a generated `headline` field; and the per-issue editor's note
needs Marco's own words.
`netlify.toml` 301s this site's own default host, `bowofdata.netlify.app`, to the
apex. **Not the same host** as the indexed duplicate seen in search: that one is
`bowlofdata.netlify.app` (with an *l*), a separate Netlify site answering 503
`usage_exceeded`, which only the Netlify dashboard can retire (see owner actions).
**Per-issue habit:** when a new week adds a variant spelling, add it to `TAG_ALIASES`.
`bowlofdata.com` is an unrelated site outside our control, so there is nothing to redirect.
Say "Bowl of Data newsletter" in full wherever the brand is written.

**Shipped 2026-09-02** — tag co-occurrence cross-links, dead-internal-link fix + build
assertion, recency in hub/tag meta descriptions, `article:*` OG timestamps and tags,
`og:type` corrected on collection pages, `Organization.founder` Person nodes.

**Shipped 2026-08-12** — dated week titles + unique descriptions, `og_title` decoupling,
headlines unlinked, JSON-LD attribution, `MIN_INDEXABLE_ITEMS` (inert), tag UTM fix,
services page rewrite, branded 404, image dimensions + `marco.jpg` 566 KB → 109 KB,
`/imgs/*` cache header. The WordPress mirror 301 was written on this date but **not actually
deployed until 2026-09-02** — see the banner at the top.

**Owner actions, blocking:**

- [x] **Deploy the WordPress retirement theme — done 2026-09-02.** `build_wp_theme.py` →
      `deploy_wp_theme.py` → `check_mirror_parity.py`, credentials from
      `../maki_newsletter/.env` (`ALTERVISTA_*`). 25/25 sampled paths 301 single-hop;
      `robots.txt` still 200; `/feed/` → `.net/feed.xml`. The feed exemption was added in
      the same pass after the first deploy 301'd subscribers to a 404.
- [ ] Leave the Altervista Search Console property in place and watch its impressions decay
      to zero — that is the consolidation working. Expect weeks, not days. Do **not** delete
      the WordPress install or release the subdomain; the 301 must keep answering.
- [ ] Re-check the `bowlofdata` (one word) query in a few weeks. That query returning the
      Altervista copy while `bowl of data` returned `.net` is the symptom this deploy fixes;
      it is the cleanest available signal that authority has consolidated.
- [ ] Set the **apex** as primary domain in Netlify to close `bowofdata.netlify.app`.
- [ ] Retire the old **`bowlofdata.netlify.app`** site (503 `usage_exceeded`, still indexed with
      old-format titles). A 503 tells Google "come back later", so it lingers; deleting the site
      turns it into a 404 and it drops out. Check it is the Postgres-era site first.
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
- [ ] After 4–8 weeks of Search Console data: raise `MIN_INDEXABLE_ITEMS` per §3. Set
      2026-08-12; **not yet due** — three weeks of data is still guessing.
- [ ] **`topic/space.html` holds 2 items from 1 issue** — thinner than any tag page, since
      hubs are created for any beat with ≥1 item while tags need 3. It is the one page on
      the site that is thin on its face rather than on a hunch. Do not delete the file (that
      404s a URL Google may already know); decide it with `MIN_INDEXABLE_ITEMS`, or give the
      hub tier its own floor that noindexes without unrendering. `topic/governance.html`
      (8 items) and `topic/quantum.html` (10) are no longer in this category.
- [ ] Per-issue OG images. All 18 week pages share one static `bowl.png` share card, so
      every Substack and social post for every issue looks identical. This is the largest
      remaining conversion lever and the only one needing a new dependency (Pillow).
- [ ] Consider full names in `FOUNDERS`. The `Person` nodes currently use the first names
      `team.html` displays; full names would resolve the entities harder, but that publishes
      more about a third party than the site does today — owner's call, not the build's.
- [ ] Look at `Week 21 · 2026` (51 articles) — every other issue holds 11–26. Likely
      predates the `fix duplicates` work.
