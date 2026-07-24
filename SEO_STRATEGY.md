# Bowl of Data — SEO, GEO & Growth Strategy

_Last updated: 2026-07-24. Owner: Marco. Companion to the code changes shipped in
`build.py` and the `templates/`. This is the "why and what next" — the code is the "how"._

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
| Topic hubs | 4 beat landing pages aggregating every issue | `site/topic/{ai,security,blockchain,engineering}.html` |
| Tag pages | 97 auto-generated technology pages (≥3 items each) | `site/tag/<slug>.html` |
| Topics index | Hub-of-hubs for internal linking + discovery | `site/topics.html` |
| Structured data | NewsArticle w/ publisher+author+image; BreadcrumbList; FAQPage; CollectionPage | `build.py` JSON-LD helpers |
| Internal linking | Beat cards, article category badges, clickable tag chips all link into hubs/tags | `index.html`, `week.html`, `topics.html` |
| GEO | `llms.txt` Topics/Tags sections + "source of record" line; E-E-A-T authorship line; freshness dates | `build.py`, `base.html` |
| Conversion | Reusable subscribe CTA on every week/hub/tag page with UTM tags | `templates/_subscribe.html` |
| OG/meta | `og:image` dimensions/alt, `og:type=article`, keyworded titles | `base.html`, `index.html` |

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
| `topic/security` | cybersecurity newsletter | weekly CVE roundup; this week in security |
| `topic/blockchain` | crypto newsletter | weekly blockchain news; stablecoin news |
| `topic/engineering` | software engineering newsletter | open-source releases this week |
| `tag/<x>` | "\<tech\> news weekly" | "\<tech\> \<recent event\>" (bitcoin, ethereum, quantum computing, llms, npm…) |
| `services` | newsletter as a service; done-for-you newsletter | AI newsletter agency; white-label newsletter |

The tag pages are the volume play: 97 of them, each a small, focused net for a long-tail
query. They cost nothing extra per issue — new tags appear automatically once a technology
hits 3 items.

---

## 4. Canonical policy (important — do not skip)

`.net` and Substack publish overlapping content. To stop them competing:

1. **`.net` pages are canonical.** Already enforced via `<link rel="canonical">`.
2. **On Substack, set each post's canonical URL to the matching `.net` page.** Substack
   supports this per-post (Settings → SEO → Canonical URL). Do it every issue, or Google may
   rank the Substack copy and we lose the on-site funnel.
3. Never publish a tag/hub page's aggregated text as a standalone Substack post — it would
   duplicate the issue pages.

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

- **Track the subscribe click** as the primary conversion event (UTM `campaign` already
  distinguishes week/topic/topics/inline sources).
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

## 9. First-30-days checklist

- [ ] Deploy the current build; confirm `sitemap.xml` lists topics + hubs + tags.
- [ ] Submit sitemap in Search Console; request indexing for `topics.html` + 4 hubs + top 10 tags.
- [ ] Set canonical URLs on the last ~8 Substack posts to their `.net` equivalents; make it a
      per-issue habit.
- [ ] Submit to 4–5 newsletter directories.
- [ ] Run the GEO spot-check and record a baseline.
- [ ] Confirm the subscribe CTA conversion event is firing in analytics.
