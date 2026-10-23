# Substack copy to paste (owner-only edit)

Prepared 2026-10-23 after reading the live Substack. Nothing here has been applied: Substack needs your sign-in.
The curation sentence is `CURATION_STATEMENT` in `build.py`; keep it word for word.

## 1. About page (Settings → About, or the About page editor)

Replace the whole body with:

> Most technical newsletters give you everything and let you figure out what matters. Bowl of Data works differently.
>
> Bowl of Data is curated by Maki, an open-source multi-agent pipeline that scans hundreds of sources every week and drafts the summaries; the Bowl of Data team reviews and publishes every issue.
>
> Every week Maki reads across AI, cybersecurity, blockchain and software engineering, ranks what it finds and drafts the summaries. Then a person on the team sits at the end of the pipeline and decides what actually makes the cut. A new issue ships every Saturday.
>
> The result is a weekly digest built on a simple principle: if it would not survive a Friday afternoon conversation with someone who knows their field, it does not go out.
>
> The full digest lives at https://bowlofdata.net, where every story gets a complete technical breakdown, source links, and tags. The Substack is the editorial layer: the 3 to 5 stories that connected into something worth reading this week, a pattern read on new model releases, and one number that reframes how you think about the week.
>
> No padding. No recycled takes. No content that exists just to fill a slot.
>
> Want to see the pipeline before you commit? Browse the archive at https://bowlofdata.net/archive.html, or read how Maki works, and get the open-source code, at https://bowlofdata.net/maki.html.
>
> The team behind the newsletter also helps companies adopt AI, builds RAG and private AI systems, and reviews AI agents for security: https://bowlofdata.net/services.html

Notes:

- The last paragraph is optional. It is the only place on Substack that points readers at the services; drop it if you want the Substack to stay purely editorial.
- Every link uses `bowlofdata.net`. The old `bowofdata.netlify.app` and the retired `bowlofdata.netlify.app` (503) are gone.
- Topics now match the site: AI, cybersecurity, blockchain and software engineering (the old text said "data infrastructure" and "emerging tech").
- The curation sentence in the second paragraph is `CURATION_STATEMENT` from `build.py`, word for word.
- "Every Saturday" matches the site; the old text had no publishing day.

## 2. Publication tagline (Settings → Publication details, the line under the name)

Now: `Weekly digest of AI, cybersecurity & data infra. Curated by a human. Processed by agents. Full digest every week`

That says the opposite of the site, where Maki curates and drafts and people review and publish. Same facts as the
site's `CURATION_STATEMENT`, cut to tagline length (use one):

1. **Recommended (109 chars):** `Weekly AI, cybersecurity, blockchain & engineering digest. Curated by Maki, reviewed and published by people.`
2. **Shorter (96 chars):** `Weekly tech digest, curated by the open-source Maki pipeline, reviewed by the Bowl of Data team.`
3. **Keeps your old rhythm (104 chars):** `Weekly digest of AI, cybersecurity & more. Curated by Maki. Reviewed by humans. Full digest on the site.`

Use "Maki" in the tagline only if you are happy for it to appear without explanation; the About page and post footer
carry the full sentence, so it resolves there.

## 3. Post footer (the "Full issue" block at the end of each post template)

Keep the existing count line. It is already correct for week 42 (20 articles, 5 papers, 7 model releases, counted separately). Add one line under it:

> Bowl of Data is curated by Maki, an open-source multi-agent pipeline that scans hundreds of sources every week and drafts the summaries; the Bowl of Data team reviews and publishes every issue. More: https://bowlofdata.net/about.html
