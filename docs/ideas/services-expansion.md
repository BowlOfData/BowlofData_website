# Services expansion: Secure door, Private AI, AI vendor report review

## Problem Statement
How might we add guardrails, secure agentic AI, content moderation, private AI and SOC2 report review to the Services page without losing the "small team, fixed scope" promise, and without publishing claims we cannot yet back?

## Recommended Direction
Three doors, each with one entry offer; everything else is a module or a one-line "also".

- **Build** (any mid-market firm): RAG Pipeline Review & Sprint (entry); Private AI Implementation (second card: the strongest proof, since we run on open local models). Custom software development drops to an "also" line.
- **Secure** (new; anyone putting agents or LLMs in front of data and tools): Agent & Guardrail Security Review (entry). Modules inside it: guardrails for private and commercial AI and for RAG, auditing and blocking unauthorized tool calls and agent actions, content moderation (toxic, biased, inaccurate output). Implementation is a separately scoped second step.
- **Assure** (regulated finance and their ICT providers): Governance Readiness Assessment (entry); LLM & Model Risk Review; AI Vendor Report Review (SOC2), framed as due diligence on the AI providers a firm relies on, mapped to ICT third-party risk expectations. It is a structured review of someone else's report, not an audit and not an attestation.

Proof wording for Secure: "we apply allowlist-gated tool access in our own pipeline; Maki is open source, so you can inspect it". Never "trusted enforcement layer": Maki is 0.x and its interfaces still change.

Copy says "reduce and evidence", never "prevent" or "guarantee".

## Key Assumptions to Validate (gate for the push, not for the build)
- [ ] Agent security is bought as a service: 5 conversations with people running agent pilots; pass = at least 3 would pay for a fixed review. Kill/reshape if fewer than 2.
- [ ] A guardrail review fits the stated duration: write the one-page scope and checklist for a real or imagined system; pass = Marco can name every deliverable and the hours behind it.
- [ ] The vendor report review has a concrete output: a checklist (scope, period, exceptions, subservice organisations, complementary controls, bridge letters) plus a one-page findings template.
- [ ] The Maki wording survives a security-literate reader: one outsider read; pass = no pushback on the claim.
- [ ] Regulatory references are right: verify the DORA third-party-risk provisions and the current BaFin position before any article number appears.
- [ ] Marco can state the regulated-industry background publicly (carried over from the pivot).

## MVP Scope
In: Secure section; Private AI card in Build; AI Vendor Report Review card in Assure; software development as an "also" line; third home-page card; "Secure enquiry" contact subject; four new FAQ entries; extra `Service` schema nodes; llms.txt and SEO_STRATEGY updates with long-tail targets.
Out: new pages, a hosted guardrail product, an open checklist (a later credibility play), pricing language, German copy.

## Success and kill criteria (6 months from push)
Success: at least 1 paid Secure or vendor-review engagement, or 3 qualified enquiries naming these offers. Reshape: enquiries come only for Build and Assure, so fold Secure into Build as a module. Kill: no enquiry for any new offer after 6 months; remove the card, keep the content as FAQ.

## Not Doing (and Why)
- Seven equal cards plus extras: dilutes focus; one entry card per door.
- Implementation inside the Secure entry offer: unscopable as fixed; separate step.
- A client's own SOC2 readiness: different, larger service.
- Claiming Maki is a certified or trusted enforcement layer: unverifiable at 0.x.
- Standalone content moderation: it overlaps the evaluation work; a module.
- Targeting head terms ("AI guardrails", "private AI"): unwinnable; long-tail and answer engines only.

## Open Questions
- Implementation boundary and durations (draft: Secure review "typically 2 to 3 weeks", vendor report review "typically 1 to 2 weeks").
- Which DORA provisions to name, if any, after verification.
- Is the push gated by the validation criteria above, or by a date?
