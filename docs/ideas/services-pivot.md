# Services pivot: practitioner-led AI engineering and assurance

## Problem Statement
How might we turn the Services and About pages from "buy a newsletter" into "hire two practitioners who run a real AI pipeline in production", so that we win 2–3 paid pilots in six months from buyers who cannot judge AI work themselves?

## Recommended Direction
Two doors on the Services page, one entry offer behind each, same two people behind both:

- **Build** (any mid-market company): optimized RAG pipeline creation and software development. Proof: Maki, a production multi-agent pipeline (11 issues shipped, 0 missed weeks, open source). Angle: auditable RAG, i.e. audit trail and data lineage, not just retrieval quality.
- **Assure** (regulated finance and their ICT providers): LLM/model risk review (evaluation framework mapped to MaRisk, DORA and, if still relevant, BAIT) and IT/data/AI governance readiness assessment (system inventory, risk classification, gap analysis, documentation roadmap). Proof: prior bank/insurer work, stated honestly.

Regulatory vocabulary appears only on the Assure side. Entry offers are fixed scope, fixed price, fixed duration: a Governance Readiness Assessment and a RAG Pipeline Review/Sprint. The other services are follow-on work.

The newsletter stays as the free flagship and proof of shipping weekly. The white-label offer is dropped. The local-models/privacy argument stays: it is the strongest differentiator for regulated buyers.

## Key Assumptions to Validate
- [ ] Newsletter readers include potential buyers: check subscriber roles or ask the next 20 contacts.
- [ ] Regulated-finance contacts will pay for a fixed-scope assessment: pitch it to 5 people before building pages.
- [ ] Prior-work claims can be stated publicly without breaching NDAs or employer rules.
- [ ] Two part-time people can deliver one assessment in 3–4 weeks.
- [ ] A concrete price on the page beats "talk to us": test with one price.
- [ ] BAIT's current status (largely superseded by DORA since Jan 2025): verify against BaFin before naming it.

## MVP Scope
**In:**
- Rewrite `site/services.html` (via `templates/services.html`) around Build and Assure, one entry offer each, short process, single contact call to action, reuse existing privacy and pipeline proof.
- Reframe About as company, newsletter as proof, and team credibility; flesh out Team bios.
- Update newsletter-on-demand SEO surfaces: titles, `llms.txt`, `llms-full.txt`, sitemap, schema.

**Out:** case-study pages, a page per service, pricing calculators, a regulation blog.

## Not Doing (and Why)
- Newsletter packages: dilutes the new message; the offer is being dropped.
- Separate sites or domains per audience: premature for a six-month test.
- Naming MaRisk/DORA to non-financial buyers: confuses them.
- Claiming certifications or client names we cannot show: credibility risk with exactly this audience.
- Building the evaluation harness as a product: sell the service first.

## Open Questions
- Which bank/insurer credentials can be stated publicly, and in what form?
- What fixed price for the assessment?
- Contact path: existing form or a booking link?
- Should the newsletter keep its current "tech digest" SEO targets while Services targets new terms? (See SEO_STRATEGY.md.)
- Next step: hand off to the planning skill for a phased page rewrite.
