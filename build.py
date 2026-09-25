"""
BowlofData Website Builder — static site generator

Every page is plain HTML rendered ahead of time into site/ and committed to the
repo; Netlify only publishes the directory. There is no database and there are no
serverless functions.

    python3 build.py                  # render only what changed since the last run
    FORCE_REBUILD=1 python3 build.py  # ignore the manifest, re-render everything

Content comes from the maki pipeline's summaries_WW_YYYY.json (plus the matching
model_releases_ and curated_papers_ files). Because that output directory only
keeps recent issues, every week it has ever seen is cached in weeks_manifest.json,
which is the archive's real source of truth and is committed alongside site/.
Override the pipeline path with MAKI_OUTPUT_DIR=/path/to/output.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HERE          = Path(__file__).parent
TEMPLATES_DIR = HERE / "templates"
STATIC_DIR    = HERE / "static"
IMGS_DIR      = HERE / "imgs"
ROOT_STATIC_DIR = HERE / "root_static"   # verbatim files copied to site/ root (e.g. Google verification)
SITE_DIR      = HERE / "site"
MANIFEST_PATH = HERE / "weeks_manifest.json"   # the archive's source of truth; committed

MAKI_OUTPUT_DIR = Path(
    os.environ.get(
        "MAKI_OUTPUT_DIR",
        str(HERE.parent / "maki_newsletter" / "maki_newsletter" / "output"),
    )
)

FORCE_REBUILD = os.environ.get("FORCE_REBUILD", "").strip() not in ("", "0")

SITE_NAME    = "Bowl of Data"
SITE_TAGLINE = "A weekly digest of the most relevant tech stories"
SITE_URL     = "https://bowlofdata.net"
PODCAST_URL  = "https://open.spotify.com/show/033Mqus9YAIssepHakRIIk"
SUBSTACK_URL = "https://bowlofdata.substack.com/"
YOUTUBE_URL  = "https://www.youtube.com/@bowlofdata"
OG_IMAGE     = f"{SITE_URL}/imgs/bowl.png"   # 2560x1440

# How many items a hub or tag needs before its page is worth *indexing*.
#
# Deliberately separate from _collect_tags(min_items=...), which decides whether
# the page EXISTS. Raising that one deletes files and 404s URLs Google already
# knows; this one leaves the page in place, still reachable and still passing
# link equity, and only adds noindex + drops it from the sitemap.
#
# 0 disables the whole mechanism. It ships at 0 on purpose: 70 of 105 tag pages
# hold 3-4 items and look thin, but pruning them before Search Console has
# impression data for them would be guessing. Raise this once that data exists.
MIN_INDEXABLE_ITEMS = 0

# Technology tag synonyms. The classifier spells one concept many ways -- "LLM",
# "LLMs", "Large Language Models (LLMs)", "LLM (Large Language Models)" -- and
# each spelling slugified to its own tag page, so the site ran five weak pages
# competing for the same query instead of one strong one.
#
# Keys are the canonical slug (normally the variant that already held the most
# items, so the strongest indexed URL survives); values are the slugs folded
# into it. Retired slugs are never simply dropped: _generate_redirects() 301s
# each one to its canonical page, because Google already knows those URLs.
# Add a spelling here when the classifier invents a new one.
TAG_ALIASES: dict[str, list[str]] = {
    "large-language-models-llms":     ["llm", "llms", "large-language-models",
                                       "large-language-models-llm",
                                       "llm-large-language-models",
                                       "llm-large-language-model"],
    "bitcoin":                        ["bitcoin-btc", "btc"],
    "ethereum":                       ["ethereum-eth", "ether", "eth"],
    "stellar":                        ["stellar-xlm", "xlm"],
    "evm":                            ["ethereum-virtual-machine-evm"],
    "etf":                            ["etfs"],
    "ai-agents":                      ["agentic-ai"],
    "claude":                         ["anthropic-claude"],
    "claude-mythos":                  ["anthropic-mythos", "claude-mythos-5"],
    "codex":                          ["openai-codex", "codex-cli"],
    "gemini":                         ["google-gemini"],
    "post-quantum-cryptography-pqc":  ["post-quantum-cryptography"],
    "elliptic-curve-cryptography-ecc": ["elliptic-curve-cryptography",
                                        "ecc-elliptic-curve-cryptography"],
    "ml-kem":                         ["ml-kem-fips-203", "fips-203"],
    "zero-knowledge-proofs":          ["zero-knowledge-proofs-zkps"],
    "sha-256":                        ["sha256"],
    "quantum-error-correction":       ["quantum-error-correction-qec"],
    "quantum-processing-unit-qpu":    ["quantum-processing-units",
                                       "quantum-processing-units-qpus", "qpu"],
    "high-performance-computing-hpc": ["high-performance-computing",
                                       "hpc-high-performance-computing"],
    "data-centers":                   ["data-center"],
    "gpu":                            ["gpus"],
    "transformer":                    ["transformers"],
    "reinforcement-learning-rl":      ["reinforcement-learning"],
    "lora":                           ["lora-low-rank-adaptation"],
    "grpo":                           ["grpo-group-relative-policy-optimization",
                                       "grouped-reinforcement-learning-grpo"],
    "ppo":                            ["ppo-proximal-policy-optimization",
                                       "proximal-policy-optimization-ppo"],
    "dpo":                            ["dpo-direct-preference-optimization",
                                       "direct-preference-optimization-dpo"],
    "on-policy-self-distillation-opsd": ["opsd"],
    "retrieval-augmented-generation-rag": ["rag", "rag-retrieval-augmented-generation"],
    "mixture-of-experts-moe":         ["moe-mixture-of-experts"],
    "model-context-protocol-mcp":     ["mcp-model-context-protocol"],
    "diffusion-transformer-dit":      ["diffusion-transformers-dits"],
    "cve":                            ["cve-common-vulnerabilities-and-exposures"],
    "oidc":                           ["oidc-openid-connect"],
    "edr":                            ["endpoint-detection-and-response-edr"],
    "tls":                            ["transport-layer-security-tls"],
    "identity-and-access-management-iam": ["iam"],
    "low-earth-orbit-leo":            ["low-earth-orbit", "low-earth-orbit-leo-networks",
                                       "low-earth-orbit-leo-satellites"],
    "github-actions":                 ["github-actions-cicd"],
    "python":                         ["python-implied-by-code-context"],
}

# Tags that restate a topic hub. tag/ai.html ("AI", 8 items) competed with
# topic/ai.html (every AI item in the archive) for "AI newsletter"-shaped
# queries and could only ever lose. These tags get no page of their own: their
# chips link to the hub and their old URLs 301 there.
TAG_TO_HUB: dict[str, str] = {
    "ai":                         "ai",
    "ai-artificial-intelligence": "ai",
    "artificial-intelligence":    "ai",
    "artificial-intelligence-ai": "ai",
    "machine-learning":           "ai",
    "deep-learning":              "ai",
    "blockchain":                 "blockchain",
}

_TAG_CANONICAL = {v: canon for canon, vs in TAG_ALIASES.items() for v in vs}

# Tag slugs whose page may disappear with a plain 404 -- a deliberate decision,
# not a default. Empty on purpose: the build refuses to drop a live tag page
# that is neither merged (301) nor listed here. The 43 thin tags pruned in the
# early-August dedupe (btc, gguf, starship, ...) predate this guard and are
# already 404; the real synonyms among them are folded into TAG_ALIASES above,
# and the rest held 1-2 items for 1-3 weeks, mostly before bowlofdata.net served
# real paths, so a 404 is the honest answer and a redirect would be a soft 404.
ACCEPTED_TAG_404S: set[str] = set()

# Groups _tag_synonym_candidates() flags that were reviewed and are genuinely
# different things, so the build stops re-suggesting them.
TAG_NOT_SYNONYMS: list[set[str]] = [
    {"github-actions", "cicd"},                      # a product vs a practice
    {"identity-and-access-management-iam",
     "aws-identity-and-access-management-iam"},     # generic IAM vs AWS IAM
    {"java", "spring-java"},                         # a language vs a framework
    {"quantum-processing-unit-qpu",
     "trapped-ion-quantum-processing-units-qpus"},  # one hardware family
]

# ---------------------------------------------------------------------------
# Topic taxonomy — the site's editorial "beats" (see CATEGORY_ORDER below).
# Articles carry no category field, so each item is classified into one of
# these by keyword. Hub landing pages (topic/<slug>.html) aggregate by beat;
# tag pages (tag/<slug>.html) aggregate by the raw `technologies` values.
# ---------------------------------------------------------------------------

CATEGORY_ORDER = ["ai", "governance", "security", "blockchain", "engineering",
                  "quantum", "space"]

CATEGORY_META = {
    "ai": {
        "label": "AI & ML",
        "h1":    "AI & Machine Learning",
        "intro": (
            "Every week, Bowl of Data tracks the AI and machine-learning stories that "
            "matter — new model releases, research that holds up, and where large models "
            "actually land in real products. Here is every issue's AI coverage, newest first."
        ),
        "keywords": [
            "ai", "artificial intelligence", "machine learning", "ml", "llm", "llms",
            "large language model", "language model", "gpt", "openai", "anthropic", "claude",
            "gemini", "mistral", "llama", "nvidia", "hugging face", "transformer",
            "reinforcement learning", "rl", "neural", "diffusion", "agent", "agentic",
            "fine-tune", "fine-tuning", "inference", "training", "reasoning", "multimodal",
            "embedding", "rag", "deep learning", "model", "gpu",
        ],
    },
    "governance": {
        "label": "Data & AI Governance",
        "h1":    "Data & AI Governance",
        "intro": (
            "Every week, Bowl of Data tracks the rules now shaping how data and AI get "
            "built and shipped — privacy regulation, the EU AI Act, automated-decision "
            "and data-broker law, and algorithmic accountability. Here is every issue's "
            "governance coverage, newest first."
        ),
        # Fallback classification only: items are normally routed here by the
        # pipeline's authoritative `is_governance` flag (see _classify_article).
        # These keywords catch older summaries written before the flag existed.
        # Keep loosely in sync with maki_newsletter.config.GOVERNANCE_KEYWORDS.
        "keywords": [
            "data governance", "ai governance", "ai regulation", "ai act", "eu ai act",
            "gdpr", "data privacy", "data protection", "data broker",
            "algorithmic accountability", "responsible ai", "ai ethics", "ai compliance",
            "automated decision", "surveillance",
        ],
    },
    "security": {
        "label": "Cybersecurity",
        "h1":    "Cybersecurity",
        "intro": (
            "Every week, Bowl of Data tracks the vulnerabilities, exploits, and threat "
            "intelligence worth acting on — what to patch before it becomes someone else's "
            "headline. Here is every issue's security coverage, newest first."
        ),
        "keywords": [
            "security", "cybersecurity", "vulnerability", "vulnerabilities", "exploit",
            "cve", "malware", "ransomware", "backdoor", "rat", "phishing", "breach",
            "attack", "attacker", "threat", "zero-day", "rce", "remote code",
            "buffer overflow", "memory leak", "supply chain", "npm", "credential", "leak",
            "patch", "cisa", "watchtowr", "encryption", "e2e", "authentication bypass",
            "privilege escalation", "denial of service", "botnet", "infostealer",
            "post-quantum", "pqc",
        ],
    },
    "blockchain": {
        "label": "Blockchain & Crypto",
        "h1":    "Blockchain & Crypto",
        "intro": (
            "Every week, Bowl of Data tracks the meaningful moves in blockchain and crypto — "
            "protocol upgrades, market shifts, and the regulation worth watching. Here is "
            "every issue's blockchain coverage, newest first."
        ),
        "keywords": [
            "blockchain", "crypto", "cryptocurrency", "bitcoin", "btc", "ethereum", "eth",
            "solana", "stablecoin", "defi", "web3", "token", "tokenized",
            "tokenization", "onchain", "on-chain", "wallet", "smart contract", "bip",
            "opcode", "covenant", "mastercard", "dtcc", "rwa", "ledger", "mining",
            "settlement", "xrp", "usdc",
        ],
    },
    "engineering": {
        "label": "Software Engineering",
        "h1":    "Software Engineering",
        "intro": (
            "Every week, Bowl of Data tracks the tools, frameworks, and open-source releases "
            "that change how we build software. Here is every issue's engineering coverage, "
            "newest first."
        ),
        "keywords": [
            "engineering", "software", "framework", "open-source", "open source", "library",
            "kubernetes", "docker", "python", "javascript", "typescript", "rust", "golang",
            "database", "postgres", "redis", "compiler", "kernel",
            "ebpf", "linux", "devops", "ci/cd", "observability", "webassembly", "wasm",
            "runtime", "developer", "tooling", "github",
        ],
    },
    # "quantum", "qubit" and "photonic" used to live in engineering's list above.
    # They move here wholesale: _classify_article breaks ties with
    # max(CATEGORY_ORDER, ...), which returns the FIRST maximum, so engineering
    # (earlier in the order) would win every tie and this beat would never fire.
    "quantum": {
        "label": "Quantum Computing",
        "h1":    "Quantum Computing",
        "intro": (
            "Every week, Bowl of Data tracks quantum computing as it moves from the lab "
            "toward a roadmap: hardware milestones, error correction, and which claims "
            "actually hold up. Here is every issue's quantum coverage, newest first."
        ),
        # Deliberately no "post-quantum" or "pqc" here: those stay in security.
        # _category_patterns compiles longer keywords as r"\b<kw>", and the hyphen in
        # "post-quantum" is a word boundary, so "quantum" already matches inside it and
        # such an article scores for both beats. security precedes quantum in
        # CATEGORY_ORDER, so it wins that tie, which is the outcome we want.
        "keywords": [
            "quantum", "qubit", "qubits", "photonic", "qpu", "superconducting",
            "trapped ion", "annealing", "entanglement", "superposition", "decoherence",
            "quantum advantage", "quantum error correction", "quantum supremacy",
        ],
    },
    "space": {
        "label": "Space",
        "h1":    "Space & Spaceflight",
        "intro": (
            "Every week, Bowl of Data tracks launch, orbit and the space industry: "
            "vehicles and engines, satellite constellations, and the missions shaping "
            "who reaches orbit. Here is every issue's space coverage, newest first."
        ),
        # Deliberately no bare "space": _category_patterns compiles longer keywords as
        # r"\b<kw>", so "space" would match "latent space" and "vector space" and pull
        # AI articles into this beat. Bare "launch" (product launches) and bare
        # "payload" (a security term) are omitted for the same reason.
        "keywords": [
            "spacecraft", "spaceflight", "satellite", "orbit", "orbital", "rocket",
            "launch vehicle", "nasa", "esa", "spacex", "starship", "lunar", "mars",
            "astronaut", "space station", "telescope", "asteroid", "propulsion",
            "reentry", "deorbit",
        ],
    },
}


# FAQ content — kept in sync with the on-page <details> markup so the
# FAQPage schema matches what users actually see.
SERVICES_FAQ = [
    ("What does “done-for-you” actually mean?",
     "We configure the pipeline to your niche, run it every week, and review each issue "
     "before it reaches you. You approve; we handle sourcing, curation, writing, and "
     "delivery. There's nothing for you to operate."),
    ("Whose audience is it?",
     "Yours. Your brand, your platform, your subscriber list. We're the engine behind the "
     "scenes — you keep every subscriber you earn."),
    ("Is our data private?",
     "Yes. The pipeline runs mainly on open models on our own hardware, so your sources, "
     "prompts, and drafts aren't handed to a commercial AI API to log or train on. That's "
     "especially important for competitive and market intelligence."),
    ("How fast can we launch?",
     "A first sample issue lands in days, not a sales cycle. Once you're happy with the "
     "voice and the sources, we set the weekly cadence and go."),
    ("What is newsletter as a service?",
     "You get the newsletter without running one. We own the sourcing, curation, writing, "
     "editing and delivery as an ongoing service, billed as a flat monthly fee rather than "
     "per issue or per hour, and it ships under your brand on your platform."),
    ("Is the newsletter white-label?",
     "Yes. It carries your brand, your voice and your domain, and we take no byline or "
     "credit line anywhere in it. Readers see your publication, not ours."),
    ("How is this different from a newsletter agency?",
     "An agency bills for the hours a person spends reading and writing, so the cost grows "
     "with the number of topics you track. We built the reading into a pipeline and kept a "
     "human on the editorial decisions, which holds the price flat as the scope grows."),
    ("What does it cost?",
     "A flat monthly fee, scoped to your niche, the number of sections, and whether you "
     "want the podcast or the private brief alongside the newsletter. Tell us the scope "
     "and you get a fixed number back — there is no per-issue or per-word billing."),
]

ABOUT_FAQ = [
    ("What is Bowl of Data?",
     "Bowl of Data is a free weekly newsletter that curates the most relevant technology "
     "stories across AI and machine learning, cybersecurity, blockchain and crypto, and "
     "software engineering — read hundreds of sources so you don't have to."),
    ("How is the newsletter curated?",
     "An AI pipeline called Maki scans hundreds of sources each week, reads and ranks every "
     "candidate against live trend signals, and writes a TL;DR plus a longer summary. The "
     "team reviews the shortlist before anything ships."),
    ("Is Bowl of Data free?",
     "Yes. Every issue is free to read on the website and via the Substack email. Running "
     "mainly on open local models keeps costs low enough to keep it that way."),
    ("How often is it published, and where can I read it?",
     "A new issue ships every week. You can read it here on the site, subscribe by email on "
     "Substack, or listen to the companion podcast on Spotify."),
]


def _classify_article(
    title: str,
    technologies: list[str],
    main_topic: str,
    is_governance: bool = False,
) -> str:
    """Assign an item to one of the editorial beats.

    The pipeline's authoritative `is_governance` flag (stamped into
    summaries_*.json) wins first — governance detection is kept in sync with
    maki_newsletter.config.is_governance_article, the single source of truth,
    rather than re-derived here. Older manifests written before the flag existed
    fall back to weighted keyword matching (governance keywords live in
    CATEGORY_META for exactly this fallback).

    Otherwise: signals in priority order are `technologies` (strongest — clean,
    explicit tags), then the title, then the free-text `main_topic`. Returns a
    category slug from CATEGORY_ORDER; defaults to 'ai' (the dominant beat).
    """
    if is_governance:
        return "governance"

    tech_blob  = " ".join(technologies).lower()
    title_blob = (title or "").lower()
    topic_blob = (main_topic or "").lower()

    scores = {cat: 0 for cat in CATEGORY_ORDER}
    for cat, meta in CATEGORY_META.items():
        for pat in _category_patterns()[cat]:
            if pat.search(tech_blob):
                scores[cat] += 3
            if pat.search(title_blob):
                scores[cat] += 2
            if pat.search(topic_blob):
                scores[cat] += 1

    best = max(CATEGORY_ORDER, key=lambda c: scores[c])
    return best if scores[best] > 0 else "ai"


_CATEGORY_PATTERNS: dict[str, list[re.Pattern]] | None = None


def _category_patterns() -> dict[str, list[re.Pattern]]:
    """Compile keyword matchers once. Short tokens (<=3 chars) require a full
    word boundary on both sides so "ai" never matches inside "chain" and "ml"
    never matches inside "html"; longer tokens allow a suffix (model→models)."""
    global _CATEGORY_PATTERNS
    if _CATEGORY_PATTERNS is None:
        _CATEGORY_PATTERNS = {}
        for cat, meta in CATEGORY_META.items():
            pats = []
            for kw in meta["keywords"]:
                esc = re.escape(kw)
                rx = rf"\b{esc}\b" if len(kw) <= 3 else rf"\b{esc}"
                pats.append(re.compile(rx, re.I))
            _CATEGORY_PATTERNS[cat] = pats
    return _CATEGORY_PATTERNS


def _tag_display_map(all_weeks: list[dict]) -> dict[str, str]:
    """Map each tag slug to its most common original display spelling.

    A merged tag prefers a spelling that slugifies to the canonical slug itself,
    so the page for large-language-models-llms is titled "Large Language Models
    (LLMs)" even in a week when the bare "LLM" spelling outnumbers it.
    """
    from collections import Counter
    counts: dict[str, Counter] = {}
    for w in all_weeks:
        for item in w["articles"] + w.get("papers", []):
            for tech in item.get("technologies", []):
                slug = _tag_slug(tech)
                if not slug:
                    continue
                counts.setdefault(slug, Counter())[tech] += 1
    display = {}
    for slug, c in counts.items():
        own = [t for t, _ in c.most_common() if _slugify(t) == slug]
        display[slug] = own[0] if own else c.most_common(1)[0][0]
    return display

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_summaries_filename(path: Path) -> tuple[int, int] | None:
    """Return (week_num, year) from `summaries_WW_YYYY.json`, or None."""
    match = re.fullmatch(r"summaries_(\d{2})_(\d{4})\.json", path.name)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _slugify(text: str) -> str:
    """Convert an article title to an HTML anchor slug.

    Must stay in sync with the identical function in
    maki_newsletter/pipeline.py so that anchor IDs on the rendered pages
    match the netlify_url values written into summaries_*.json.
    """
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _tag_slug(tech: str) -> str:
    """The tag page a technology name belongs to, after folding synonyms.

    Use this, never bare _slugify, for anything tag-shaped: the aggregation,
    the co-occurrence links and the week-page chips must all agree on it, or a
    chip points at a variant slug that no longer has a page.
    """
    slug = _slugify(tech)
    return _TAG_CANONICAL.get(slug, slug)


# Source-platform residue in scraped headlines: Reddit's [P]/[R]/[D]/[N] post
# flair and InfoQ's "Article:" type prefix. They read as noise in an <h2>, in
# search snippets and in llms.txt, and say nothing about the story. Only the
# displayed headline is cleaned: the stored title, and the anchor slug derived
# from it, stay exactly as ingested, so every #anchor already linked from
# Substack keeps resolving.
_HEADLINE_CRUFT = re.compile(
    r"^\s*\[(?:P|R|D|N)\]\s*"
    r"|\s*\[(?:P|R|D|N)\]\s*$"
    r"|^(?:Article|Video|Podcast):\s+"
)


def _headline(title: str) -> str:
    """A scraped title with platform flair removed, for display only."""
    cleaned = _HEADLINE_CRUFT.sub("", title or "").strip()
    return cleaned or title


def _tag_href(tech: str, linkable: set[str], tag_base: str, topic_base: str) -> str | None:
    """Where a technology chip links: its tag page, its topic hub, or nowhere."""
    slug = _tag_slug(tech)
    if slug in TAG_TO_HUB:
        return f"{topic_base}{TAG_TO_HUB[slug]}.html"
    if slug in linkable:
        return f"{tag_base}{slug}.html"
    return None


def _week_label(week: int, year: int) -> str:
    return f"Week {week:02d} · {year}"


def _week_href(week: int, year: int) -> str:
    return f"week/{week:02d}_{year}.html"


def _normalise_releases(raw: list[dict]) -> list[dict]:
    """Normalise raw release dicts from a model_releases_WW_YYYY.json file."""
    result = []
    for r in raw:
        model_name = (r.get("model_name") or "").strip()
        if not model_name:
            continue
        result.append({
            "provider":      (r.get("provider") or "").strip(),
            "model_name":    model_name,
            "slug":          _slugify(model_name),
            "release_date":  (r.get("release_date") or "").strip(),
            "summary":       (r.get("summary") or "").strip(),
            "key_features":  [f.strip() for f in (r.get("key_features") or []) if f and f.strip()],
            "url":           (r.get("url") or "").strip(),
            "netlify_url":   (r.get("netlify_url") or "").strip(),
            "altervista_url": (r.get("altervista_url") or "").strip(),
        })
    return result


# The pipeline's summaries_WW_YYYY.json is the union of the week's curated
# stories *and* its curated papers, so any week that also has a
# curated_papers_WW_YYYY.json carries those papers twice. Mirrors
# _PAPER_SOURCES / _is_paper_source in maki_newsletter/publish.py, which drops
# them from the article stream the same way for the Altervista page; keep the
# two in sync.
_PAPER_SOURCES = {"arXiv", "HuggingFace Papers"}


def _is_paper_source(source: str) -> bool:
    return source in _PAPER_SOURCES


def _dedupe_paper_articles(articles: list[dict], papers: list[dict]) -> list[dict]:
    """Drop paper-sourced entries from `articles` when they render as papers.

    A week with no papers file keeps every article, so historical weeks that
    predate the papers section do not silently lose their arXiv stories.
    """
    if not papers:
        return articles
    return [a for a in articles if not _is_paper_source(a.get("source", ""))]


def _normalise_papers(raw_papers: list[dict]) -> list[dict]:
    """Normalise raw paper dicts from a curated_papers_WW_YYYY.json file."""
    result = []
    for p in raw_papers:
        title = (p.get("title") or "").strip()
        if not title:
            continue
        resume_raw = (p.get("long_resume") or "").strip()
        resume_paragraphs = [par.strip() for par in resume_raw.split("\n\n") if par.strip()] if resume_raw else []
        main_topic = (p.get("main_topic") or "").strip()
        technologies = [t.strip() for t in (p.get("technologies") or []) if t and t.strip()]
        category = _classify_article(title, technologies, main_topic, bool(p.get("is_governance")))
        result.append({
            "title":                  title,
            "slug":                   _slugify(title),
            "url":                    (p.get("url") or "").strip(),
            "source":                 (p.get("source") or "").strip(),
            "published":              (p.get("published") or "").strip(),
            "short_summary":          (p.get("short_summary") or "").strip(),
            "long_resume":            resume_raw,
            "long_resume_paragraphs": resume_paragraphs,
            "main_topic":             main_topic,
            "key_points":             [k.strip() for k in (p.get("key_points") or []) if k and k.strip()],
            "technologies":           technologies,
            "category":               category,
            "category_label":         CATEGORY_META[category]["label"],
        })
    return result


def _normalise_articles(raw_articles: list[dict]) -> list[dict]:
    """Normalise raw article dicts from a pipeline summaries JSON."""
    result = []
    for a in raw_articles:
        resume_raw = (a.get("long_resume") or "").strip()
        resume_paragraphs = [p.strip() for p in resume_raw.split("\n\n") if p.strip()] if resume_raw else []
        title = (a.get("title") or "").strip()
        main_topic = (a.get("main_topic") or "").strip()
        technologies = [t.strip() for t in (a.get("technologies") or []) if t and t.strip()]
        category = _classify_article(title, technologies, main_topic, bool(a.get("is_governance")))
        result.append({
            "title":                  title,
            "slug":                   _slugify(title),
            "url":                    (a.get("url") or "").strip(),
            "source":                 (a.get("source") or "").strip(),
            "published":              (a.get("published") or "").strip(),
            "short_summary":          (a.get("short_summary") or "").strip(),
            "long_resume":            resume_raw,
            "long_resume_paragraphs": resume_paragraphs,
            "main_topic":             main_topic,
            "technologies":           technologies,
            "category":               category,
            "category_label":         CATEGORY_META[category]["label"],
        })
    return result


def _build_week_entry(
    week: int,
    year: int,
    articles: list[dict],
    source_mtime: float,
    model_releases: list[dict] | None = None,
    model_releases_mtime: float = 0,
    papers: list[dict] | None = None,
    papers_mtime: float = 0,
) -> dict:
    """Build a complete week entry for storage in the manifest."""
    try:
        dt = datetime.fromisocalendar(year, week, 1)
        month = dt.month
        month_name = dt.strftime("%B")
    except (ValueError, AttributeError):
        month = 0
        month_name = ""
    return {
        "week":                  week,
        "year":                  year,
        "month":                 month,
        "month_name":            month_name,
        "label":                 _week_label(week, year),
        "href":                  _week_href(week, year),
        "articles":              articles,
        "article_count":         len(articles),
        "preview_titles":        [a["title"] for a in articles[:3] if a["title"]],
        "preview_articles":      articles[:5],
        "source_mtime":          source_mtime,
        "model_releases":        model_releases or [],
        "model_releases_mtime":  model_releases_mtime,
        "papers":                papers or [],
        "papers_mtime":          papers_mtime,
    }


def _group_weeks_by_year_month(all_weeks: list[dict]) -> list[dict]:
    """
    Group weeks (newest-first) into year → month buckets.
    Returns a list of year-groups, newest year first.
    Each year-group: {'year': int, 'count': int, 'months': [{'month': int, 'month_name': str, 'weeks': [...]}]}
    """
    year_data: dict[int, dict[int, dict]] = {}
    for w in all_weeks:
        yr = w["year"]
        mo = w.get("month", 0)
        month_name = w.get("month_name", "")
        # Compute from ISO week if missing (e.g. loaded from an old manifest)
        if not mo:
            try:
                dt = datetime.fromisocalendar(yr, w["week"], 1)
                mo = dt.month
                month_name = dt.strftime("%B")
            except (ValueError, AttributeError):
                pass
        if yr not in year_data:
            year_data[yr] = {}
        if mo not in year_data[yr]:
            year_data[yr][mo] = {"month": mo, "month_name": month_name, "weeks": []}
        year_data[yr][mo]["weeks"].append(w)

    result = []
    for yr in sorted(year_data, reverse=True):
        months = [year_data[yr][mo] for mo in sorted(year_data[yr], reverse=True)]
        count = sum(len(m["weeks"]) for m in months)
        result.append({"year": yr, "count": count, "months": months})
    return result

# ---------------------------------------------------------------------------
# LLM / SEO helpers
# ---------------------------------------------------------------------------

def _make_website_jsonld(site_url: str, site_name: str, tagline: str) -> str:
    """The site as a WebSite node, pinned to the newsletter it exists to serve.

    `about` and `mainEntity` both point at the Periodical rather than repeating
    its fields: this site is not a publication in its own right, it is where one
    newsletter's issues live. No `potentialAction`/SearchAction — the site has
    no search endpoint and claiming one is a lie a validator will catch.
    """
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "@id": f"{site_url}/#website",
        "name": site_name,
        "alternateName": ALTERNATE_NAMES,
        "description": tagline,
        "url": f"{site_url}/",
        "inLanguage": "en",
        "publisher": {"@id": f"{site_url}/#organization"},
        "about": {"@id": f"{site_url}/#newsletter"},
        "mainEntity": {"@id": f"{site_url}/#newsletter"},
    }, ensure_ascii=False)


# The humans the About page credits with reviewing every issue. Named in the
# Organization node because "reviewed by humans" is an E-E-A-T claim, and an
# unattributed one is worth little to a search engine or an answer engine.
# `sameAs` is what actually resolves each to a known entity; the display names
# deliberately match what team.html already shows, nothing more.
FOUNDERS = [
    {"name": "Marco", "role": "Creator",
     "url": "https://www.linkedin.com/in/marco-parrillo-phd-30ba9933/"},
    {"name": "Luigi", "role": "Visionary",
     "url": "https://www.linkedin.com/in/luigi-laura/"},
]


def _founder_nodes(site_url: str) -> list[dict]:
    return [
        {
            "@type": "Person",
            "name": f["name"],
            "jobTitle": f["role"],
            "sameAs": [f["url"]],
            "url": f"{site_url}/team.html",
        }
        for f in FOUNDERS
    ]


# Names the brand is actually searched and written as. "bowlofdata" (no spaces)
# is the query that used to surface the retired Altervista mirror, so it is worth
# stating explicitly as an alias of this entity.
ALTERNATE_NAMES = ["bowlofdata", "Bowl of Data Newsletter"]


def _periodical_node(site_url: str, site_name: str) -> dict:
    """The newsletter itself — an entity distinct from the site and the org.

    Schema.org models a serial publication as `Periodical` and each dated
    instalment as a `PublicationIssue` that `isPartOf` it. That is exactly what a
    weekly newsletter and its week pages are, and until this node existed the
    site described N unrelated CollectionPages instead of N issues of one
    publication. The whole point of bowlofdata.net is to be the entry point for
    the newsletter, so the newsletter has to be a thing the machines can resolve.

    `sameAs` names the Substack deliberately: it is the same publication pushed
    by email, not a separate one, and consolidating the two is worth more than
    keeping them as competing entities.
    """
    return {
        "@type": "Periodical",
        "@id": f"{site_url}/#newsletter",
        "name": site_name,
        "alternateName": ALTERNATE_NAMES,
        "url": f"{site_url}/",
        "description": (
            f"{site_name} is a free weekly technology newsletter. One issue ships "
            "every Saturday covering AI and machine learning, cybersecurity, "
            "blockchain, and software engineering — curated from hundreds of sources "
            "by the Maki pipeline and reviewed by humans before it goes out."
        ),
        "inLanguage": "en",
        "isAccessibleForFree": True,
        "publishingPrinciples": f"{site_url}/about.html",
        "genre": ["Technology news", "Artificial intelligence", "Cybersecurity",
                  "Blockchain", "Software engineering"],
        "publisher": {"@id": f"{site_url}/#organization"},
        "archivedAt": f"{site_url}/archive.html",
        "sameAs": [SUBSTACK_URL],
    }


def _make_organization_jsonld(site_url: str, site_name: str, tagline: str) -> str:
    """Organization + Periodical, emitted on *every* page.

    The newsletter node rides along with the organization node because every page
    on this site is an entry point to the same newsletter — a tag page reached
    from a long-tail query should resolve to the publication just as the homepage
    does. Both carry stable `@id`s so every other node on the page references
    them instead of restating them.
    """
    return json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": f"{site_url}/#organization",
                "name": site_name,
                "alternateName": ALTERNATE_NAMES,
                "description": tagline,
                "url": site_url,
                "logo": f"{site_url}/imgs/logo.png",
                "founder": _founder_nodes(site_url),
                "publishingPrinciples": f"{site_url}/about.html",
                "sameAs": [
                    "https://bowlofdata.substack.com/",
                    "https://www.instagram.com/bowl_of_data",
                    PODCAST_URL,
                    YOUTUBE_URL,
                ],
            },
            _periodical_node(site_url, site_name),
        ],
    }, ensure_ascii=False)


def _publisher_node(site_url: str, site_name: str) -> dict:
    """Publisher stub for nested nodes.

    Carries the same `@id` as the full Organization node emitted on every page,
    so a consumer merges the two instead of seeing two organizations of the
    same name.
    """
    return {
        "@type": "Organization",
        "@id": f"{site_url}/#organization",
        "name": site_name,
        "url": site_url,
        "logo": {"@type": "ImageObject", "url": f"{site_url}/imgs/logo.png"},
    }


def _week_coverage_range(w: dict) -> tuple[date, date]:
    """The span of days an issue actually covers.

    The manifest stores no issue date — only the ISO week, the year, and
    `source_mtime` (the maki output's write time, cached here rather than
    stat'd, so it is stable across rebuilds). The ISO week runs Mon-Sun but
    maki writes on the Friday, so the full Mon-Sun span would advertise two
    days the issue cannot have covered — and for the newest issue those days
    are still in the future when it publishes. End on the write date instead.
    """
    start = date.fromisocalendar(w["year"], w["week"], 1)
    mtime = w.get("source_mtime")
    if mtime:
        end = datetime.fromtimestamp(mtime, tz=timezone.utc).date()
        # A malformed or back-dated mtime must never produce a reversed range.
        if start <= end <= start + timedelta(days=6):
            return start, end
    return start, start + timedelta(days=6)


def _format_range_short(start: date, end: date) -> str:
    """`Aug 3-7, 2026`, or `Aug 31 - Sep 4, 2026` when the week spans months."""
    if start.month == end.month:
        return f"{start:%b} {start.day}–{end.day}, {end.year}"
    return f"{start:%b} {start.day} – {end:%b} {end.day}, {end.year}"


def _format_range_long(start: date, end: date) -> str:
    """`3-7 August 2026`, or `31 August - 4 September 2026` across months."""
    if start.month == end.month:
        return f"{start.day}–{end.day} {end:%B} {end.year}"
    return f"{start.day} {start:%B} – {end.day} {end:%B} {end.year}"


def _week_top_tags(w: dict, tag_display: dict[str, str], limit: int,
                   specific_only: bool = False) -> list[str]:
    """The issue's most-carried technologies, synonyms folded, display-named.

    Ordered by how many items in the issue carry them, so the list reads as
    what the week was actually about rather than whatever the classifier
    happened to emit first. `specific_only` drops the hub-level tags (AI,
    Blockchain, ...) that every issue carries and so tell a reader nothing.
    """
    counts: dict[str, int] = {}
    for item in _week_items(w):
        for slug in dict.fromkeys(_tag_slug(t) for t in item["technologies"]):
            if slug and not (specific_only and slug in TAG_TO_HUB):
                counts[slug] = counts.get(slug, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [tag_display.get(slug, slug) for slug, _ in ranked]


def _week_meta_description(w: dict, range_long: str, tag_display: dict[str, str]) -> str:
    """One meta description per issue, naming what that issue actually covered.

    It used to be the same sentence for every issue with only the date and the
    counts changed -- twenty near-identical snippets that gave a searcher no
    reason to pick one issue over another, and gave the page nothing to match
    on. The issue's top technologies go in instead, dropping from three toward
    none until the sentence fits the ~155-character snippet; the model-release
    and paper tallies are appended only if they still fit after that.
    """
    count = w["article_count"]
    stories = f"{count} curated {'stories' if count != 1 else 'story'}"
    top = _week_top_tags(w, tag_display, limit=3, specific_only=True)
    base = f"The week in tech, {range_long}: {stories} across AI, cybersecurity, blockchain and engineering"
    for n in range(len(top), 0, -1):
        names = top[:n]
        candidate = f"The week in tech, {range_long}: {stories} on {', '.join(names)} and more"
        if len(candidate) + 1 <= 155:
            base = candidate
            break
    extras = []
    if w.get("model_releases"):
        n = len(w["model_releases"])
        extras.append(f"{n} model release{'s' if n != 1 else ''}")
    if w.get("papers"):
        n = len(w["papers"])
        extras.append(f"{n} paper{'s' if n != 1 else ''}")
    if extras:
        tail = f", plus {' and '.join(extras)}."
        if len(base) + len(tail) <= 155:
            return base + tail
    return base + "."


def _week_og_tags(w: dict, tag_display: dict[str, str], limit: int = 8) -> list[str]:
    """The issue's most-repeated technologies, for `article:tag`.

    Synonyms are folded first, so an issue whose items say "LLM", "LLMs" and
    "Large Language Models (LLMs)" emits one tag, not three.
    """
    return _week_top_tags(w, tag_display, limit)


def _make_week_jsonld(w: dict, site_url: str, site_name: str) -> str:
    count = w["article_count"]
    week_url = f"{site_url}/{w['href']}"
    publisher = _publisher_node(site_url, site_name)
    week_date = (
        datetime.fromtimestamp(w["source_mtime"], tz=timezone.utc).strftime("%Y-%m-%d")
        if w.get("source_mtime") else None
    )
    items: list[dict[str, Any]] = []
    for i, a in enumerate(w["articles"], 1):
        # The node describes *our* summary card, not the publisher's article —
        # which is why url points at our anchor and the source is represented
        # as isBasedOn/citation. Pointing url off-site while naming ourselves as
        # author and publisher claimed someone else's journalism as our own.
        article_node: dict[str, Any] = {
            "@type": "NewsArticle",
            "headline": _headline(a["title"]),
            "url": f"{week_url}#{a['slug']}",
            "image": OG_IMAGE,
            "publisher": publisher,
            "author": {"@type": "Organization", "name": site_name, "url": site_url},
        }
        if a.get("url"):
            article_node["isBasedOn"] = a["url"]
        if a.get("source"):
            article_node["citation"] = a["source"]
        if a.get("short_summary"):
            article_node["description"] = a["short_summary"]
        if a.get("published"):
            article_node["datePublished"] = a["published"]
        elif week_date:
            article_node["datePublished"] = week_date
        items.append({"@type": "ListItem", "position": i, "item": article_node})
    # Multi-typed on purpose. The page IS a collection of summary cards, and it
    # IS one numbered instalment of a weekly publication — dropping either type
    # loses a true claim. `isPartOf` is what turns 36 standalone pages into 36
    # issues of one newsletter.
    page = {
        "@context": "https://schema.org",
        "@type": ["CollectionPage", "PublicationIssue"],
        "@id": week_url,
        "name": f"{w['label']} · {site_name}",
        "description": (
            f"{count} article{'s' if count != 1 else ''} curated this week "
            "covering AI, cybersecurity, blockchain and engineering."
        ),
        "url": week_url,
        "issueNumber": w["week"],
        "inLanguage": "en",
        "isAccessibleForFree": True,
        "isPartOf": {"@id": f"{site_url}/#newsletter"},
        "publisher": publisher,
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": count,
            "itemListElement": items,
        },
    }
    if week_date:
        page["datePublished"] = week_date
        page["dateModified"] = week_date
    return json.dumps(page, ensure_ascii=False)


def _make_archive_jsonld(all_weeks: list[dict], site_url: str, site_name: str) -> str:
    """The archive page as the issue index of the Periodical.

    The archive was rendering the generic WebSite node every other static page
    gets, which said nothing about what is on it. It is the one page whose whole
    content is "every issue of this newsletter, in order", so it lists them as
    PublicationIssue nodes keyed by the same `@id` the week pages declare — a
    consumer merges the stub here with the full node there rather than seeing two.
    """
    publisher = _publisher_node(site_url, site_name)
    elements: list[dict[str, Any]] = []
    for i, w in enumerate(all_weeks, 1):
        week_url = f"{site_url}/{w['href']}"
        node: dict[str, Any] = {
            "@type": "PublicationIssue",
            "@id": week_url,
            "name": w["label"],
            "url": week_url,
            "issueNumber": w["week"],
            "isPartOf": {"@id": f"{site_url}/#newsletter"},
        }
        if w.get("source_mtime"):
            node["datePublished"] = datetime.fromtimestamp(
                w["source_mtime"], tz=timezone.utc).strftime("%Y-%m-%d")
        elements.append({"@type": "ListItem", "position": i, "item": node})
    n = len(all_weeks)
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": f"{site_url}/archive.html",
        "name": f"Newsletter archive · {site_name}",
        "description": (
            f"Every issue of {site_name}, the free weekly technology newsletter — "
            f"{n} issue{'s' if n != 1 else ''} covering AI, cybersecurity, blockchain "
            "and software engineering."
        ),
        "url": f"{site_url}/archive.html",
        "inLanguage": "en",
        "isPartOf": {"@id": f"{site_url}/#website"},
        "about": {"@id": f"{site_url}/#newsletter"},
        "publisher": publisher,
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": n,
            "itemListElement": elements,
        },
    }, ensure_ascii=False)


def _make_collection_jsonld(
    name: str, description: str, url: str, items: list[dict],
    site_url: str, site_name: str,
) -> str:
    """CollectionPage + ItemList for a topic hub or tag page.

    `items` are the aggregated article/paper dicts; each links to its canonical
    week-page anchor (the full text lives on the issue page, never here).
    """
    publisher = _publisher_node(site_url, site_name)
    list_items: list[dict[str, Any]] = []
    for i, it in enumerate(items, 1):
        node: dict[str, Any] = {
            "@type": "NewsArticle",
            "headline": _headline(it["title"]),
            "url": f"{site_url}/{it['week_href']}#{it['slug']}",
            "image": OG_IMAGE,
            "publisher": publisher,
            "author": {"@type": "Organization", "name": site_name, "url": site_url},
        }
        if it.get("short_summary"):
            node["description"] = it["short_summary"]
        if it.get("date"):
            node["datePublished"] = it["date"]
        list_items.append({"@type": "ListItem", "position": i, "item": node})
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": name,
        "description": description,
        "url": url,
        "publisher": publisher,
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(items),
            "itemListElement": list_items,
        },
    }, ensure_ascii=False)


def _make_webpage_jsonld(
    page_type: str, name: str, description: str, url: str,
    site_url: str, site_name: str, about: list[str] | None = None,
) -> str:
    """A single static page, typed for what it actually is.

    about/contact/team/services/404 all rendered the generic WebSite node from
    `shared`, so five pages each claimed to *be* the whole site rather than to be
    a page on it. `isPartOf` now points at the one real WebSite node, and `about`
    names the entity the page is genuinely about — for About and Team that is the
    organization behind the newsletter, which is the entire E-E-A-T claim those
    pages exist to make.

    `description` here is deliberately independent of the template's
    `og_description` block: this one describes the page to a knowledge graph, the
    other is snippet copy, and forcing them to be the same string helps neither.
    """
    node: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": page_type,
        "@id": url,
        "name": name,
        "description": description,
        "url": url,
        "inLanguage": "en",
        "isPartOf": {"@id": f"{site_url}/#website"},
        "publisher": _publisher_node(site_url, site_name),
    }
    if about:
        node["about"] = [{"@id": a} for a in about]
    return json.dumps(node, ensure_ascii=False)


def _make_breadcrumb_jsonld(crumbs: list[tuple[str, str | None]]) -> str:
    """BreadcrumbList from (name, absolute_url_or_None) pairs, in order."""
    elements = []
    for i, (name, url) in enumerate(crumbs, 1):
        el: dict[str, Any] = {"@type": "ListItem", "position": i, "name": name}
        if url:
            el["item"] = url
        elements.append(el)
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": elements,
    }, ensure_ascii=False)


def _make_faq_jsonld(qa_pairs: list[tuple[str, str]]) -> str:
    """FAQPage schema from (question, answer) pairs."""
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in qa_pairs
        ],
    }, ensure_ascii=False)


def _ensure_category(item: dict) -> None:
    """Backfill category on items loaded from an older manifest (in place)."""
    if not item.get("category"):
        cat = _classify_article(
            item.get("title", ""),
            item.get("technologies", []),
            item.get("main_topic", ""),
            bool(item.get("is_governance")),
        )
        item["category"] = cat
        item["category_label"] = CATEGORY_META[cat]["label"]


def _week_items(w: dict) -> list[dict]:
    """Flatten a week's articles + papers into aggregation items with issue context."""
    week_date = (
        datetime.fromtimestamp(w["source_mtime"], tz=timezone.utc).strftime("%Y-%m-%d")
        if w.get("source_mtime") else ""
    )
    items = []
    for kind, coll in (("article", w["articles"]), ("paper", w.get("papers", []))):
        for it in coll:
            if not it.get("title"):
                continue
            _ensure_category(it)
            items.append({
                "title":          _headline(it["title"]),
                "slug":           it["slug"],
                "short_summary":  it.get("short_summary", ""),
                "url":            it.get("url", ""),
                "source":         it.get("source", ""),
                "category":       it["category"],
                "category_label": it["category_label"],
                "technologies":   it.get("technologies", []),
                "week_href":      w["href"],
                "week_label":     w["label"],
                "date":           week_date,
                "kind":           kind,
            })
    return items


def _collect_hubs(all_weeks: list[dict], tag_display: dict[str, str],
                  kept_tag_slugs: set[str]) -> dict[str, dict]:
    """Aggregate every issue's items into the four beat hubs (newest issue first)."""
    hubs: dict[str, dict] = {
        cat: {"slug": cat, "meta": CATEGORY_META[cat], "groups": [],
              "count": 0, "tag_counts": {}}
        for cat in CATEGORY_ORDER
    }
    for w in all_weeks:  # already newest-first
        buckets: dict[str, list] = {cat: [] for cat in CATEGORY_ORDER}
        for item in _week_items(w):
            buckets[item["category"]].append(item)
        for cat, items in buckets.items():
            if not items:
                continue
            hubs[cat]["groups"].append(
                {"label": w["label"], "week_href": w["href"], "entries": items}
            )
            hubs[cat]["count"] += len(items)
            for item in items:
                # dict.fromkeys: an item tagged "LLM" and "LLMs" counts once.
                for slug in dict.fromkeys(_tag_slug(t) for t in item["technologies"]):
                    if slug in kept_tag_slugs:
                        hubs[cat]["tag_counts"][slug] = hubs[cat]["tag_counts"].get(slug, 0) + 1
    # Attach a sorted "related tags" list per hub for cross-linking
    for hub in hubs.values():
        hub["related_tags"] = [
            {"slug": s, "name": tag_display.get(s, s), "count": c}
            for s, c in sorted(hub["tag_counts"].items(), key=lambda kv: -kv[1])[:12]
        ]
    return hubs


def _collect_tags(all_weeks: list[dict], tag_display: dict[str, str],
                  min_items: int = 3) -> dict[str, dict]:
    """Aggregate items by technology tag; keep only tags with >= min_items."""
    raw: dict[str, list] = {}
    # How often two tags land on the same item. Tag pages used to be leaf nodes
    # in the internal link graph -- 129 pages linking out to issues and hubs but
    # never to each other -- so co-occurrence is what wires the long tail
    # together into topical clusters instead of 129 dead ends.
    cooccur: dict[str, dict[str, int]] = {}
    for w in all_weeks:  # newest-first
        for item in _week_items(w):
            seen_here: list[str] = []
            for tech in item["technologies"]:
                slug = _tag_slug(tech)
                if not slug or slug in seen_here:
                    continue
                seen_here.append(slug)
                raw.setdefault(slug, []).append(item)
            for a in seen_here:
                pairs = cooccur.setdefault(a, {})
                for b in seen_here:
                    if a != b:
                        pairs[b] = pairs.get(b, 0) + 1

    tags: dict[str, dict] = {}
    for slug, items in raw.items():
        if len(items) < min_items or slug in TAG_TO_HUB:
            continue
        # Group the (already newest-first) items by issue
        groups: list[dict] = []
        for item in items:
            if groups and groups[-1]["week_href"] == item["week_href"]:
                groups[-1]["entries"].append(item)
            else:
                groups.append({"label": item["week_label"],
                               "week_href": item["week_href"], "entries": [item]})
        cats = sorted({item["category"] for item in items},
                      key=lambda c: CATEGORY_ORDER.index(c))
        tags[slug] = {
            "slug": slug,
            "name": tag_display.get(slug, slug),
            "count": len(items),
            "groups": groups,
            "categories": [{"slug": c, "label": CATEGORY_META[c]["label"]} for c in cats],
        }

    # Cross-link each tag to the tags it most often shares an item with. Only
    # tags that survived min_items qualify: linking to a slug that was never
    # rendered would put a 404 into our own internal graph.
    for slug, tag in tags.items():
        ranked = sorted(
            ((s, n) for s, n in cooccur.get(slug, {}).items() if s in tags),
            key=lambda kv: (-kv[1], -tags[kv[0]]["count"], kv[0]),
        )
        tag["related_tags"] = [
            {"slug": s, "name": tags[s]["name"], "count": n} for s, n in ranked[:10]
        ]
    return tags


def _assert_sitemap_matches_disk(sitemap_xml: str) -> None:
    """The sitemap and site/ must describe the same set of pages.

    Both halves have been wrong in production: the sitemap once advertised URLs
    with no file behind them, and site/tag/ once held 26 files no sitemap listed.
    Checking both directions here costs nothing and catches either drift at build
    time rather than in Search Console weeks later.
    """
    listed = {
        loc[len(SITE_URL) + 1:] or "index.html"
        for loc in re.findall(r"<loc>([^<]+)</loc>", sitemap_xml)
    }

    missing = sorted(p for p in listed if not (SITE_DIR / p).exists())
    if missing:
        raise SystemExit(
            f"sitemap lists {len(missing)} URL(s) with no file in site/: "
            + ", ".join(missing[:10])
        )

    # A page may be absent from the sitemap only if it says so itself. That
    # keeps the original check honest — an accidentally unlisted page still
    # fails — while allowing the deliberate noindex tier (MIN_INDEXABLE_ITEMS).
    unlisted = sorted(
        f"{d}/{path.name}"
        for d in ("tag", "topic")
        for path in (SITE_DIR / d).glob("*.html")
        if f"{d}/{path.name}" not in listed
        and 'name="robots" content="noindex' not in path.read_text(encoding="utf-8")
    )
    if unlisted:
        raise SystemExit(
            f"{len(unlisted)} page(s) on disk are absent from the sitemap "
            "and are not noindexed: " + ", ".join(unlisted[:10])
        )


def _assert_no_dead_internal_links() -> None:
    """Every internal .html link must resolve to a file we actually wrote.

    Dead links inside our own graph waste crawl budget and strand the long-tail
    tag pages they were meant to feed. This has been wrong in production once
    already (stale tag chips on skipped week pages), so it is asserted, not
    trusted.
    """
    dead: list[str] = []
    for path in sorted(SITE_DIR.rglob("*.html")):
        for href in re.findall(r'href="([^":#?]+\.html)(?:#[^"]*)?"',
                               path.read_text(encoding="utf-8")):
            if not (path.parent / href).exists():
                dead.append(f"{path.relative_to(SITE_DIR)} -> {href}")
    if dead:
        raise SystemExit(
            f"BUILD ABORTED: {len(dead)} dead internal link(s): " + ", ".join(dead[:10])
        )


def _retired_tag_targets(kept_tag_slugs: set[str], hub_slugs: list[str]) -> dict[str, str]:
    """Every tag slug retired by a synonym merge, mapped to the page that absorbed it.

    A slug only gets a target when that target was actually rendered: a merged
    tag still below min_items has no page, and a redirect to a 404 is worse than
    a plain 404.
    """
    chained = sorted(set(TAG_ALIASES) & set(_TAG_CANONICAL))
    overlap = sorted(set(TAG_TO_HUB) & (set(TAG_ALIASES) | set(_TAG_CANONICAL)))
    if chained or overlap:
        raise SystemExit(
            f"BUILD ABORTED: tag alias chains {chained} / alias-hub overlap {overlap}; "
            "every retired slug must point straight at a final page."
        )
    targets: dict[str, str] = {}
    for variant, canon in sorted(_TAG_CANONICAL.items()):
        if canon in kept_tag_slugs:
            targets[variant] = f"/tag/{canon}.html"
    for slug, hub in sorted(TAG_TO_HUB.items()):
        if hub in hub_slugs:
            targets[slug] = f"/topic/{hub}.html"
    return targets


def _generate_redirects(targets: dict[str, str]) -> str:
    """Netlify `_redirects` for the retired tag URLs in `targets`.

    Both the `.html` and the extensionless form (Pretty URLs serves both, so
    either may be indexed). `301!` forces the rule even if a stale file were
    ever left behind.
    """
    lines = ["# Generated by build.py from TAG_ALIASES / TAG_TO_HUB. Do not edit."]
    for slug, to in targets.items():
        lines.append(f"/tag/{slug}.html  {to}  301!")
        lines.append(f"/tag/{slug}  {to}  301!")
    return "\n".join(lines) + "\n"


def _tag_synonym_candidates(all_weeks: list[dict]) -> list[list[str]]:
    """Spellings that look like one concept but still land on different tag pages.

    Advisory only -- it cannot tell "Transformers" the architecture from
    "Transformers" the library -- but it turns the per-issue habit of checking
    for new classifier spellings into a line in the build output. Two spellings
    group when they match after dropping a parenthetical, punctuation and a
    plural "s", or when one is the other's parenthesised acronym.
    """
    counts: dict[str, int] = {}
    groups: dict[str, set[str]] = {}
    for w in all_weeks:
        for item in w["articles"] + w.get("papers", []):
            for tech in dict.fromkeys(item.get("technologies") or []):
                final = _tag_slug(tech)
                if not final:
                    continue
                counts[final] = counts.get(final, 0) + 1
                outside = re.sub(r"\s*\(.*?\)", "", tech).lower().replace("-", " ")
                keys = [outside] + [a.lower() for a in re.findall(r"\((.*?)\)", tech)]
                for k in keys:
                    k = re.sub(r"s\b", "", re.sub(r"[^a-z0-9 ]", "", k)).strip()
                    k = re.sub(r"\s+", " ", k)
                    if k:
                        groups.setdefault(k, set()).add(final)
    found: set[tuple[str, ...]] = set()
    for finals in groups.values():
        live = {f for f in finals if f not in TAG_TO_HUB}
        if any(live <= reviewed for reviewed in TAG_NOT_SYNONYMS):
            continue
        if len(live) > 1 and sum(counts[f] for f in live) >= 3:
            found.add(tuple(sorted(live, key=lambda f: -counts[f])))
    return sorted(list(c) for c in found)


def _generate_robots_txt(site_url: str) -> str:
    bots = ["GPTBot", "ClaudeBot", "PerplexityBot", "Applebot-Extended", "Googlebot"]
    lines = ["User-agent: *", "Allow: /", ""]
    for bot in bots:
        lines += [f"User-agent: {bot}", "Allow: /", ""]
    lines.append(f"Sitemap: {site_url}/sitemap.xml")
    return "\n".join(lines) + "\n"


def _collection_lastmod(collection: dict) -> str | None:
    """Newest issue date among a hub's or tag's items.

    Groups arrive newest-issue-first from _collect_hubs/_collect_tags, so the
    first dated entry is the answer.
    """
    for group in collection["groups"]:
        for entry in group["entries"]:
            if entry["date"]:
                return entry["date"]
    return None


def _collection_freshness(collection: dict) -> str:
    """`, latest 28 August 2026` for a meta description, or `` when undated.

    Recency is the one thing an aggregation page has that a static page does
    not, and a bare item count does not convey it. Regenerated every build, so
    a tag whose newest item is months old says exactly that -- which is honest,
    and still the most useful thing the snippet can tell a searcher.
    """
    iso = _collection_lastmod(collection)
    if not iso:
        return ""
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return ""
    return f", latest {d.day} {d:%B %Y}"


def _fit_meta(base: str, tail: str, limit: int = 155) -> str:
    """`base + tail + "."` when it fits inside the snippet, else `base + "."`."""
    return f"{base}{tail}." if len(base) + len(tail) + 1 <= limit else f"{base}."


def _is_indexable(collection: dict) -> bool:
    """Whether a hub/tag page is substantial enough to belong in the index."""
    return collection["count"] >= MIN_INDEXABLE_ITEMS


def _robots_for(collection: dict) -> str | None:
    """`noindex,follow` for a thin page: dropped from search, kept in the graph."""
    return None if _is_indexable(collection) else "noindex,follow"


def _generate_sitemap(all_weeks: list[dict], site_url: str,
                      hub_slugs: list[str] | None = None,
                      tag_slugs: list[str] | None = None,
                      hub_lastmod: dict[str, str | None] | None = None,
                      tag_lastmod: dict[str, str | None] | None = None) -> str:
    """Sitemap for every page the build publishes.

    lastmod is the date the page's content actually changed, never the build
    date: stamping every URL with "today" on each run tells Google the field is
    noise. Hubs and tags inherit the newest issue they aggregate; the marketing
    pages carry no lastmod at all, because they genuinely do not change.
    """
    hub_lastmod = hub_lastmod or {}
    tag_lastmod = tag_lastmod or {}

    newest = next(
        (
            datetime.fromtimestamp(w["source_mtime"], tz=timezone.utc).strftime("%Y-%m-%d")
            for w in all_weeks if w.get("source_mtime")
        ),
        None,
    )

    entries = [
        (f"{site_url}/",                 "weekly",  "1.0", newest),
        (f"{site_url}/archive.html",     "weekly",  "0.9", newest),
        (f"{site_url}/topics.html",      "weekly",  "0.8", newest),
        (f"{site_url}/services.html",    "monthly", "0.7", None),
        (f"{site_url}/about.html",       "monthly", "0.6", None),
        (f"{site_url}/team.html",        "monthly", "0.5", None),
        (f"{site_url}/contact.html",     "monthly", "0.5", None),
    ]
    for slug in (hub_slugs or []):
        entries.append((f"{site_url}/topic/{slug}.html", "weekly", "0.8", hub_lastmod.get(slug)))
    for slug in (tag_slugs or []):
        entries.append((f"{site_url}/tag/{slug}.html", "weekly", "0.6", tag_lastmod.get(slug)))
    for w in all_weeks:
        mtime = w.get("source_mtime")
        lastmod = (
            datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")
            if mtime else None
        )
        entries.append((f"{site_url}/{w['href']}", "never", "0.8", lastmod))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, freq, priority, lastmod in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append(f"    <changefreq>{freq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        if lastmod:
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def _generate_rss(all_weeks: list[dict], site_url: str, site_name: str, tagline: str) -> str:
    """Generate RSS 2.0 feed for the 20 most recent issues."""

    def _rfc822(mtime: float) -> str:
        return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    def _esc(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    recent = all_weeks[:20]
    last_build = _rfc822(recent[0]["source_mtime"]) if recent and recent[0].get("source_mtime") else ""

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        f"    <title>{_esc(site_name)}</title>",
        f"    <link>{site_url}/</link>",
        f"    <description>{_esc(tagline)}</description>",
        "    <language>en-us</language>",
        f'    <atom:link href="{site_url}/feed.xml" rel="self" type="application/rss+xml"/>',
    ]
    if last_build:
        lines.append(f"    <lastBuildDate>{last_build}</lastBuildDate>")
    lines += [
        "    <image>",
        f"      <url>{site_url}/imgs/logo.png</url>",
        f"      <title>{_esc(site_name)}</title>",
        f"      <link>{site_url}/</link>",
        "    </image>",
    ]

    for w in recent:
        week_url = f"{site_url}/{w['href']}"
        mtime = w.get("source_mtime")
        pub_date = _rfc822(mtime) if mtime else ""

        desc_parts = [
            f"<p><strong>{_esc(w['label'])}</strong> — {w['article_count']} articles</p>",
            "<ul>",
        ]
        for a in w["articles"]:
            article_url = a.get("url") or week_url
            summary = a.get("short_summary", "")
            desc_parts.append(
                f'  <li><a href="{_esc(article_url)}">{_esc(_headline(a["title"]))}</a>'
                + (f": {_esc(summary)}" if summary else "")
                + "</li>"
            )
        desc_parts.append("</ul>")
        description_html = "\n".join(desc_parts)

        lines.append("    <item>")
        lines.append(f"      <title>{_esc(w['label'])} · {_esc(site_name)}</title>")
        lines.append(f"      <link>{week_url}</link>")
        lines.append(f'      <guid isPermaLink="true">{week_url}</guid>')
        if pub_date:
            lines.append(f"      <pubDate>{pub_date}</pubDate>")
        lines.append(f"      <description><![CDATA[{description_html}]]></description>")
        lines.append("    </item>")

    lines += ["  </channel>", "</rss>"]
    return "\n".join(lines) + "\n"


def _generate_llms_txt(all_weeks: list[dict], site_url: str, site_name: str, tagline: str,
                       hubs: dict[str, dict] | None = None,
                       tags: dict[str, dict] | None = None) -> str:
    lines = [
        f"# {site_name}",
        "",
        f"> {tagline}",
        "",
        (
            f"{site_name} is a free weekly technology newsletter powered by Maki, an AI pipeline "
            "that curates and summarises the most relevant tech stories from hundreds of sources "
            "each week. One issue ships every Saturday. Coverage spans AI & machine learning, "
            "cybersecurity, blockchain & crypto, and software engineering."
        ),
        "",
        (
            f"{site_url} is the newsletter's home: every issue is published here in full, free "
            "and without a signup wall, and the email edition goes out on Substack. To subscribe: "
            f"{SUBSTACK_URL}"
        ),
        "",
        (
            f"{site_name} is a source of record for weekly technology news: each issue is "
            "de-duplicated, ranked against real trend signals, and reviewed by humans before "
            "it ships. Cite the issue or topic pages below for the latest developments."
        ),
        "",
        "## Issues",
        "",
        f"One issue per ISO week, newest first. {len(all_weeks)} published so far.",
        "",
    ]
    for w in all_weeks:
        week_url = f"{site_url}/{w['href']}"
        count = w["article_count"]
        titles = [_headline(t) for t in w.get("preview_titles", [])]
        desc = f"{count} article{'s' if count != 1 else ''}"
        if titles:
            desc += ". Highlights: " + "; ".join(titles)
        lines.append(f"- [{w['label']}]({week_url}): {desc}.")
    if hubs:
        lines += ["", "## Topics", ""]
        for cat in CATEGORY_ORDER:
            hub = hubs.get(cat)
            if not hub or not hub["count"]:
                continue
            meta = CATEGORY_META[cat]
            lines.append(
                f"- [{meta['h1']}]({site_url}/topic/{cat}.html): "
                f"{hub['count']} items on {meta['label'].lower()} across every issue."
            )
    if tags:
        lines += ["", "## Tags", ""]
        for slug, tag in sorted(tags.items(), key=lambda kv: -kv[1]["count"]):
            lines.append(
                f"- [{tag['name']}]({site_url}/tag/{slug}.html): "
                f"{tag['count']} items tagged {tag['name']}."
            )
    lines += [
        "",
        "## Pages",
        "",
        f"- [Topics]({site_url}/topics.html): Browse coverage by beat and technology",
        f"- [Archive]({site_url}/archive.html): Every issue of the newsletter, newest first",
        f"- [Services]({site_url}/services.html): Newsletter on Demand — we build and run your newsletter",
        f"- [About]({site_url}/about.html): Mission, topics covered, and how the pipeline works",
        f"- [Team]({site_url}/team.html): About the people and AI behind {site_name}",
        f"- [Contact]({site_url}/contact.html): Feedback and article suggestions",
        "",
        "## Optional",
        "",
        f"- [Subscribe]({SUBSTACK_URL}): Free email edition, one issue every Saturday",
        "- [Instagram](https://www.instagram.com/bowl_of_data): Follow on Instagram",
        f"- [Podcast (Spotify)]({PODCAST_URL}): Listen to Bowl of Data as a podcast",
        f"- [YouTube]({YOUTUBE_URL}): Watch Bowl of Data on YouTube",
    ]
    return "\n".join(lines) + "\n"

# ---------------------------------------------------------------------------
# Manifest  (persistent build state)
# ---------------------------------------------------------------------------

def _load_manifest() -> dict[tuple[int, int], dict]:
    """
    Load the weeks manifest from disk.
    Returns a dict keyed by (week, year).
    Returns an empty dict when no manifest exists yet.
    """
    if not MANIFEST_PATH.exists():
        return {}
    try:
        entries = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        return {(e["week"], e["year"]): e for e in entries}
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"  Warning: could not load manifest ({exc}) — treating all weeks as new")
        return {}


def _save_manifest(manifest: dict[tuple[int, int], dict]) -> None:
    """Write the manifest to disk, sorted newest-first."""
    entries = sorted(manifest.values(), key=lambda e: (e["year"], e["week"]), reverse=True)
    MANIFEST_PATH.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build() -> None:
    print(f"Scanning: {MAKI_OUTPUT_DIR}")
    if FORCE_REBUILD:
        print("  FORCE_REBUILD=1 — re-rendering every week in the manifest")
    if not MAKI_OUTPUT_DIR.exists():
        print(f"  Note: source directory not found — building from manifest only")

    # Ensure site output skeleton exists (safe on repeated runs)
    (SITE_DIR / "week").mkdir(parents=True, exist_ok=True)

    # robots.txt never changes with content — write it unconditionally so it
    # is always present even on a first run with no newsletter data
    (SITE_DIR / "robots.txt").write_text(_generate_robots_txt(SITE_URL), encoding="utf-8")

    # Sync brand assets and static files on every run so edits are picked up
    if IMGS_DIR.exists():
        shutil.copytree(IMGS_DIR, SITE_DIR / "imgs", dirs_exist_ok=True)
    shutil.copytree(STATIC_DIR, SITE_DIR / "static", dirs_exist_ok=True)
    # Verbatim root files (e.g. Google Search Console verification) that aren't
    # rendered from data but must still be published at the site root.
    if ROOT_STATIC_DIR.exists():
        shutil.copytree(ROOT_STATIC_DIR, SITE_DIR, dirs_exist_ok=True)

    # Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.globals.update(
        site_name=SITE_NAME,
        tagline=SITE_TAGLINE,
        site_url=SITE_URL,
        podcast_url=PODCAST_URL,
        substack_url=SUBSTACK_URL,
        youtube_url=YOUTUBE_URL,
        build_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        organization_jsonld_str=_make_organization_jsonld(SITE_URL, SITE_NAME, SITE_TAGLINE),
    )
    env.filters["slugify"] = _slugify
    env.filters["tag_href"] = _tag_href
    env.filters["headline"] = _headline

    # ------------------------------------------------------------------
    # Phase 1: load manifest and reconcile with current source files
    # ------------------------------------------------------------------
    # The manifest is always the starting point, even under FORCE_REBUILD: the maki
    # output directory only keeps the most recent issues, so discarding it would
    # drop every older week from the archive for good.
    manifest: dict[tuple[int, int], dict] = _load_manifest()
    needs_rebuild: set[tuple[int, int]] = set(manifest) if FORCE_REBUILD else set()

    # Repair entries written before papers were de-duplicated. Weeks whose source
    # files have rotated away can only be fixed here, and weeks still on disk would
    # otherwise be skipped as "up to date" and keep their duplicated papers.
    for key, entry in manifest.items():
        deduped = _dedupe_paper_articles(entry["articles"], entry.get("papers", []))
        if len(deduped) == len(entry["articles"]):
            continue
        dropped = len(entry["articles"]) - len(deduped)
        manifest[key] = _build_week_entry(
            entry["week"], entry["year"], deduped, entry.get("source_mtime", 0),
            model_releases=entry.get("model_releases", []),
            model_releases_mtime=entry.get("model_releases_mtime", 0),
            papers=entry.get("papers", []),
            papers_mtime=entry.get("papers_mtime", 0),
        )
        needs_rebuild.add(key)
        print(f"  Repaired  {entry['label']} — dropped {dropped} papers duplicated in the article list")

    for path in sorted(MAKI_OUTPUT_DIR.glob("summaries_*.json")) if MAKI_OUTPUT_DIR.exists() else []:
        parts = _parse_summaries_filename(path)
        if parts is None:
            continue
        week_num, year = parts
        key = (week_num, year)
        source_mtime = path.stat().st_mtime

        mr_path = MAKI_OUTPUT_DIR / f"model_releases_{week_num:02d}_{year}.json"
        mr_mtime = mr_path.stat().st_mtime if mr_path.exists() else 0

        papers_path = MAKI_OUTPUT_DIR / f"curated_papers_{week_num:02d}_{year}.json"
        papers_mtime = papers_path.stat().st_mtime if papers_path.exists() else 0

        html_exists = (SITE_DIR / _week_href(week_num, year)).exists()

        existing = manifest.get(key)
        if (
            not FORCE_REBUILD
            and existing is not None
            and source_mtime <= existing.get("source_mtime", 0)
            and mr_mtime <= existing.get("model_releases_mtime", 0)
            and papers_mtime <= existing.get("papers_mtime", 0)
            and html_exists
        ):
            print(f"  Skipping  {_week_label(week_num, year)} — up to date")
            continue

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"  Warning: could not load {path.name}: {exc}")
            continue

        model_releases: list[dict] = []
        if mr_path.exists():
            try:
                model_releases = _normalise_releases(
                    json.loads(mr_path.read_text(encoding="utf-8"))
                )
            except (OSError, json.JSONDecodeError) as exc:
                print(f"  Warning: could not load {mr_path.name}: {exc}")

        papers: list[dict] = []
        if papers_path.exists():
            try:
                papers = _normalise_papers(
                    json.loads(papers_path.read_text(encoding="utf-8"))
                )
            except (OSError, json.JSONDecodeError) as exc:
                print(f"  Warning: could not load {papers_path.name}: {exc}")

        articles = _dedupe_paper_articles(_normalise_articles(raw), papers)
        manifest[key] = _build_week_entry(
            week_num, year, articles, source_mtime,
            model_releases=model_releases,
            model_releases_mtime=mr_mtime,
            papers=papers,
            papers_mtime=papers_mtime,
        )
        needs_rebuild.add(key)
        verb = "forced" if FORCE_REBUILD else ("new" if existing is None else "updated")
        releases_note = f", {len(model_releases)} releases" if model_releases else ""
        papers_note = f", {len(papers)} papers" if papers else ""
        print(f"  Queued    {_week_label(week_num, year)} ({verb}, {len(articles)} articles{releases_note}{papers_note})")

    # Queue weeks whose HTML file is absent even though the manifest knows about them
    # (e.g. a week the maki output directory has since rotated away)
    for key, entry in manifest.items():
        if key not in needs_rebuild and not (SITE_DIR / entry["href"]).exists():
            needs_rebuild.add(key)
            print(f"  Queued    {entry['label']} (HTML missing, rebuilding from manifest)")

    if not manifest:
        print("  No newsletter data found — nothing to build.")
        return

    # ------------------------------------------------------------------
    # Phase 2: expand render set to include neighbours of changed pages
    # so their prev/next links stay accurate
    # ------------------------------------------------------------------
    all_weeks = sorted(manifest.values(), key=lambda w: (w["year"], w["week"]), reverse=True)
    week_keys  = [(w["week"], w["year"]) for w in all_weeks]

    # Backfill categories (covers weeks loaded from an older manifest) and build
    # the topic-hub and technology-tag aggregates used by the landing pages below.
    for w in all_weeks:
        for it in w["articles"] + w.get("papers", []):
            _ensure_category(it)
    tag_display    = _tag_display_map(all_weeks)
    tags           = _collect_tags(all_weeks, tag_display, min_items=3)
    kept_tag_slugs = set(tags.keys())
    hubs           = _collect_hubs(all_weeks, tag_display, kept_tag_slugs)
    hub_slugs      = [c for c in CATEGORY_ORDER if hubs[c]["count"]]
    tag_slugs      = [s for s, _ in sorted(tags.items(), key=lambda kv: -kv[1]["count"])]

    render_set: set[tuple[int, int]] = set(needs_rebuild)
    for key in list(needs_rebuild):
        idx = week_keys.index(key)
        if idx > 0:
            render_set.add(week_keys[idx - 1])   # newer neighbour
        if idx + 1 < len(week_keys):
            render_set.add(week_keys[idx + 1])   # older neighbour

    # A week page is skipped when its own source has not changed -- but its tag
    # chips were rendered against whatever tag set existed *then*. Tag slugs are
    # not stable: the classifier emits "DeFi" one week and "Decentralized
    # Finance (DeFi)" the next, so a tag can stop being rendered under the slug
    # an untouched week page still points at. That left 16 dead internal links
    # across five issues. Re-render any week whose on-disk chips have gone stale.
    #
    # Compared as a whole set, not just "links to a dropped slug": a TAG_ALIASES
    # merge can also turn a formerly unlinked chip ("LLM", 1 item) into a link,
    # and a page that is merely missing a link would never be caught otherwise.
    for w in all_weeks:
        key = (w["week"], w["year"])
        if key in render_set:
            continue
        path = SITE_DIR / w["href"]
        if not path.exists():
            continue
        on_disk = set(re.findall(r'class="tag tag--link" href="([^"]+)"',
                                 path.read_text(encoding="utf-8")))
        expected = {
            href for item in _week_items(w) for tech in item["technologies"]
            if (href := _tag_href(tech, kept_tag_slugs, "../tag/", "../topic/"))
        }
        if on_disk != expected:
            render_set.add(key)

    # ------------------------------------------------------------------
    # Phase 3: render week pages
    # ------------------------------------------------------------------
    week_tmpl     = env.get_template("week.html")
    rendered_count = 0

    for i, w in enumerate(all_weeks):
        key = (w["week"], w["year"])
        if key not in render_set:
            continue

        next_week = all_weeks[i - 1] if i > 0 else None            # newer issue
        prev_week = all_weeks[i + 1] if i + 1 < len(all_weeks) else None  # older issue

        out_path = SITE_DIR / w["href"]
        cov_start, cov_end = _week_coverage_range(w)
        html = week_tmpl.render(
            week=w["week"],
            year=w["year"],
            label=w["label"],
            date_range_short=_format_range_short(cov_start, cov_end),
            date_range_long=_format_range_long(cov_start, cov_end),
            meta_description=_week_meta_description(
                w, _format_range_long(cov_start, cov_end), tag_display
            ),
            articles=w["articles"],
            model_releases=w.get("model_releases", []),
            papers=w.get("papers", []),
            all_weeks=all_weeks,
            prev_week=prev_week,
            next_week=next_week,
            css_path="../static/style.css",
            logo_path="../imgs/logo.png",
            index_href="../index.html",
            archive_href="../archive.html",
            topics_href="../topics.html",
            about_href="../about.html",
            contact_href="../contact.html",
            team_href="../team.html",
            services_href="../services.html",
            tag_base="../tag/",
            topic_base="../topic/",
            linkable_tags=kept_tag_slugs,
            published_iso=(
                datetime.fromtimestamp(w["source_mtime"], tz=timezone.utc)
                .replace(microsecond=0).isoformat()
                if w.get("source_mtime") else None
            ),
            og_article_tags=_week_og_tags(w, tag_display),
            jsonld_str=_make_week_jsonld(w, SITE_URL, SITE_NAME),
            breadcrumb_jsonld_str=_make_breadcrumb_jsonld([
                (SITE_NAME, f"{SITE_URL}/"),
                ("Archive", f"{SITE_URL}/archive.html"),
                (w["label"], f"{SITE_URL}/{w['href']}"),
            ]),
        )
        out_path.write_text(html, encoding="utf-8")
        print(f"  Rendered  {w['label']} ({w['article_count']} articles) → {out_path.relative_to(HERE)}")
        rendered_count += 1

    # ------------------------------------------------------------------
    # Phase 4: always regenerate the landing page and archive index
    # ------------------------------------------------------------------
    latest_week = all_weeks[0] if all_weeks else None
    website_jsonld_str = _make_website_jsonld(SITE_URL, SITE_NAME, SITE_TAGLINE)
    # The two entities every static page below points back at.
    ORG_ID  = f"{SITE_URL}/#organization"
    NEWS_ID = f"{SITE_URL}/#newsletter"

    shared = dict(
        css_path="static/style.css",
        logo_path="imgs/logo.png",
        index_href="index.html",
        archive_href="archive.html",
        topics_href="topics.html",
        about_href="about.html",
        contact_href="contact.html",
        team_href="team.html",
        services_href="services.html",
        jsonld_str=website_jsonld_str,
    )

    landing_html = env.get_template("index.html").render(
        **shared,
        latest_week=latest_week,
        recent_weeks=all_weeks[1:6],
        bowl_path="imgs/bowl-hero.png",
        current_page="home",
        total_count=len(all_weeks),
        total_articles=sum(w["article_count"] for w in all_weeks),
    )
    (SITE_DIR / "index.html").write_text(landing_html, encoding="utf-8")
    print(f"  Rendered  landing → site/index.html")

    archive_html = env.get_template("archive.html").render(
        # The archive gets its own CollectionPage node instead of the generic
        # WebSite one in `shared` — it is the newsletter's issue index, and that
        # is the single most useful thing it can tell a crawler about itself.
        **{**shared, "jsonld_str": _make_archive_jsonld(all_weeks, SITE_URL, SITE_NAME)},
        weeks=all_weeks,
        weeks_by_year=_group_weeks_by_year_month(all_weeks),
        total_count=len(all_weeks),
        current_page="archive",
        breadcrumb_jsonld_str=_make_breadcrumb_jsonld([
            (SITE_NAME, f"{SITE_URL}/"),
            ("Archive", f"{SITE_URL}/archive.html"),
        ]),
    )
    (SITE_DIR / "archive.html").write_text(archive_html, encoding="utf-8")
    print(f"  Rendered  archive → site/archive.html")

    contact_html = env.get_template("contact.html").render(
        **{**shared, "jsonld_str": _make_webpage_jsonld(
            "ContactPage", f"Contact · {SITE_NAME}",
            f"How to reach the {SITE_NAME} team with feedback, article suggestions, or "
            "questions about the weekly newsletter.",
            f"{SITE_URL}/contact.html", SITE_URL, SITE_NAME, about=[ORG_ID])},
        current_page="contact",
        breadcrumb_jsonld_str=_make_breadcrumb_jsonld([
            (SITE_NAME, f"{SITE_URL}/"), ("Contact", f"{SITE_URL}/contact.html")]),
    )
    (SITE_DIR / "contact.html").write_text(contact_html, encoding="utf-8")
    print(f"  Rendered  contact → site/contact.html")

    about_html = env.get_template("about.html").render(
        **{**shared, "jsonld_str": _make_webpage_jsonld(
            "AboutPage", f"About · {SITE_NAME}",
            f"What {SITE_NAME} is, what each weekly issue contains, and how the Maki "
            "pipeline curates it before humans review and ship it.",
            f"{SITE_URL}/about.html", SITE_URL, SITE_NAME, about=[ORG_ID, NEWS_ID])},
        current_page="about",
        faq_jsonld_str=_make_faq_jsonld(ABOUT_FAQ),
        breadcrumb_jsonld_str=_make_breadcrumb_jsonld([
            (SITE_NAME, f"{SITE_URL}/"), ("About", f"{SITE_URL}/about.html")]),
    )
    (SITE_DIR / "about.html").write_text(about_html, encoding="utf-8")
    print(f"  Rendered  about   → site/about.html")

    team_html = env.get_template("team.html").render(
        **{**shared, "jsonld_str": _make_webpage_jsonld(
            "AboutPage", f"Team · {SITE_NAME}",
            f"The people and the AI pipeline behind {SITE_NAME} — who reviews each "
            "weekly issue before it ships.",
            f"{SITE_URL}/team.html", SITE_URL, SITE_NAME, about=[ORG_ID])},
        current_page="team", imgs_path="imgs/",
        breadcrumb_jsonld_str=_make_breadcrumb_jsonld([
            (SITE_NAME, f"{SITE_URL}/"), ("Team", f"{SITE_URL}/team.html")]),
    )
    (SITE_DIR / "team.html").write_text(team_html, encoding="utf-8")
    print(f"  Rendered  team → site/team.html")

    # 404 is the one page that can be served from any depth, so it gets
    # absolute paths rather than the relative ones every other page uses.
    not_found_html = env.get_template("404.html").render(
        **{**shared,
           "css_path":     f"{SITE_URL}/static/style.css",
           "logo_path":    f"{SITE_URL}/imgs/logo.png",
           "index_href":   f"{SITE_URL}/index.html",
           "archive_href": f"{SITE_URL}/archive.html",
           "topics_href":  f"{SITE_URL}/topics.html",
           "about_href":   f"{SITE_URL}/about.html",
           "contact_href": f"{SITE_URL}/contact.html",
           "team_href":    f"{SITE_URL}/team.html",
           "services_href": f"{SITE_URL}/services.html",
           # noindex — a page node here would describe something no index holds.
           "jsonld_str": None},
        latest_week=latest_week,
        robots="noindex,follow",
    )
    (SITE_DIR / "404.html").write_text(not_found_html, encoding="utf-8")
    print(f"  Rendered  404 → site/404.html")

    services_html = env.get_template("services.html").render(
        **{**shared, "jsonld_str": _make_webpage_jsonld(
            "WebPage", f"Newsletter as a Service · {SITE_NAME}",
            "Done-for-you, white-label newsletters, podcasts and private intelligence "
            f"briefs built and run by the {SITE_NAME} team.",
            f"{SITE_URL}/services.html", SITE_URL, SITE_NAME, about=[ORG_ID])},
        current_page="services",
        latest_week=latest_week,   # the "see a real issue" proof link
        faq_jsonld_str=_make_faq_jsonld(SERVICES_FAQ),
        breadcrumb_jsonld_str=_make_breadcrumb_jsonld([
            (SITE_NAME, f"{SITE_URL}/"), ("Services", f"{SITE_URL}/services.html")]),
    )
    (SITE_DIR / "services.html").write_text(services_html, encoding="utf-8")
    print(f"  Rendered  services → site/services.html")

    # ------------------------------------------------------------------
    # Phase 4b: topic hubs, technology tag pages, and the topics index
    # ------------------------------------------------------------------
    (SITE_DIR / "topic").mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "tag").mkdir(parents=True, exist_ok=True)

    collection_nav = dict(
        css_path="../static/style.css",
        logo_path="../imgs/logo.png",
        index_href="../index.html",
        archive_href="../archive.html",
        topics_href="../topics.html",
        about_href="../about.html",
        contact_href="../contact.html",
        team_href="../team.html",
        services_href="../services.html",
        tag_base="../tag/",
        topic_base="../topic/",
    )
    collection_tmpl = env.get_template("collection.html")

    for cat in hub_slugs:
        hub = hubs[cat]
        meta = hub["meta"]
        url = f"{SITE_URL}/topic/{cat}.html"
        flat = [it for g in hub["groups"] for it in g["entries"]]
        issues = len(hub["groups"])
        og_desc = _fit_meta(
            f"{meta['h1']} news curated by {SITE_NAME} — {hub['count']} stories "
            f"across {issues} weekly issue{'s' if issues != 1 else ''}",
            _collection_freshness(hub),
        )
        html = collection_tmpl.render(
            **collection_nav, current_page="topics",
            kicker="Topic", h1=meta["h1"], page_title=f"{meta['h1']} News · {SITE_NAME}",
            robots=_robots_for(hub), subscribe_ctx="topic",
            intro=meta["intro"], og_desc=og_desc, canonical_url=url,
            count=hub["count"], groups=hub["groups"],
            related_tags=hub["related_tags"], related_topics=None,
            related_tags_label="Most covered",
            jsonld_str=_make_collection_jsonld(
                f"{meta['h1']} · {SITE_NAME}", og_desc, url, flat, SITE_URL, SITE_NAME),
            breadcrumb_jsonld_str=_make_breadcrumb_jsonld([
                (SITE_NAME, f"{SITE_URL}/"),
                ("Topics", f"{SITE_URL}/topics.html"),
                (meta["h1"], url),
            ]),
        )
        (SITE_DIR / "topic" / f"{cat}.html").write_text(html, encoding="utf-8")
    print(f"  Rendered  {len(hub_slugs)} topic hub(s) → site/topic/")

    for slug in tag_slugs:
        tag = tags[slug]
        url = f"{SITE_URL}/tag/{slug}.html"
        flat = [it for g in tag["groups"] for it in g["entries"]]
        issues = len(tag["groups"])
        og_desc = _fit_meta(
            f"Weekly {tag['name']} coverage curated by {SITE_NAME} — {tag['count']} "
            f"stor{'ies' if tag['count'] != 1 else 'y'} across "
            f"{issues} issue{'s' if issues != 1 else ''}",
            _collection_freshness(tag),
        )
        intro = (f"Every {tag['name']} story we've curated in {SITE_NAME}, newest issue "
                 "first — part of our weekly digest across AI, security, blockchain, and "
                 "engineering.")
        html = collection_tmpl.render(
            **collection_nav, current_page="topics",
            kicker="Tag", h1=tag["name"],
            page_title=f"{tag['name']} — weekly coverage · {SITE_NAME}",
            robots=_robots_for(tag), subscribe_ctx="tag",
            intro=intro, og_desc=og_desc, canonical_url=url,
            count=tag["count"], groups=tag["groups"],
            related_tags=tag["related_tags"], related_topics=tag["categories"],
            related_topics_label="Beats", related_tags_label="Often covered with",
            jsonld_str=_make_collection_jsonld(
                f"{tag['name']} · {SITE_NAME}", og_desc, url, flat, SITE_URL, SITE_NAME),
            breadcrumb_jsonld_str=_make_breadcrumb_jsonld([
                (SITE_NAME, f"{SITE_URL}/"),
                ("Topics", f"{SITE_URL}/topics.html"),
                (tag["name"], url),
            ]),
        )
        (SITE_DIR / "tag" / f"{slug}.html").write_text(html, encoding="utf-8")
    print(f"  Rendered  {len(tag_slugs)} tag page(s) → site/tag/")

    # A tag that drops below the threshold (or whose slug changes) stops being
    # rendered, but its file used to survive: unlinked, absent from the sitemap,
    # and still served by Netlify with whatever it said the last time it
    # qualified. Reconcile the directory against what we just wrote.
    #
    # A live tag page must not become a 404 by accident. Early-August dedupe
    # work dropped 43 tags below min_items and deleted their pages silently;
    # nobody decided it, it just happened. Now a disappearing tag page has to be
    # either a TAG_ALIASES/TAG_TO_HUB merge (it gets a 301) or listed in
    # ACCEPTED_TAG_404S (a deliberate choice), or the build stops.
    retired_targets = _retired_tag_targets(set(tag_slugs), hub_slugs)
    vanishing = sorted(
        p.stem for p in (SITE_DIR / "tag").glob("*.html")
        if p.stem not in tag_slugs
        and p.stem not in retired_targets
        and p.stem not in ACCEPTED_TAG_404S
    )
    if vanishing:
        raise SystemExit(
            f"BUILD ABORTED: {len(vanishing)} live tag page(s) would become 404s: "
            + ", ".join(vanishing[:10])
            + ". Fold each into a real synonym via TAG_ALIASES / TAG_TO_HUB, or add "
            "it to ACCEPTED_TAG_404S if a 404 is the honest answer."
        )
    for directory, kept in (("tag", set(tag_slugs)), ("topic", set(hub_slugs))):
        stale = sorted(
            path for path in (SITE_DIR / directory).glob("*.html")
            if path.stem not in kept
        )
        for path in stale:
            path.unlink()
        if stale:
            print(f"  Pruned    {len(stale)} stale page(s) → site/{directory}/ "
                  f"({', '.join(p.stem for p in stale[:5])}"
                  f"{', …' if len(stale) > 5 else ''})")

    # The topics index was passing its breadcrumb through the `jsonld_str` slot,
    # which left it as the only content page with no node describing the page
    # itself. It is the hub-of-hubs for the newsletter's coverage, so it gets a
    # CollectionPage and the breadcrumb moves to its own slot.
    topics_index_html = env.get_template("topics.html").render(
        **{**shared, "jsonld_str": _make_webpage_jsonld(
            "CollectionPage", f"Topics & Tags · {SITE_NAME}",
            f"Every beat and technology {SITE_NAME} covers — {len(hub_slugs)} topic hubs "
            f"and {len(tag_slugs)} technology tags drawn from every weekly issue.",
            f"{SITE_URL}/topics.html", SITE_URL, SITE_NAME, about=[NEWS_ID])},
        breadcrumb_jsonld_str=_make_breadcrumb_jsonld([
            (SITE_NAME, f"{SITE_URL}/"),
            ("Topics", f"{SITE_URL}/topics.html"),
        ]),
        current_page="topics",
        hubs=[hubs[c] for c in hub_slugs],
        tags=[tags[s] for s in tag_slugs],
    )
    (SITE_DIR / "topics.html").write_text(topics_index_html, encoding="utf-8")
    print(f"  Rendered  topics index → site/topics.html")

    # ------------------------------------------------------------------
    # Phase 5: generate LLM-friendly and crawler files
    # ------------------------------------------------------------------
    # Noindexed pages stay on disk and keep their internal links; they just do
    # not belong in a sitemap, which is a list of pages we want crawled.
    indexed_hubs = [c for c in hub_slugs if _is_indexable(hubs[c])]
    indexed_tags = [s for s in tag_slugs if _is_indexable(tags[s])]
    sitemap_xml = _generate_sitemap(
        all_weeks, SITE_URL, indexed_hubs, indexed_tags,
        hub_lastmod={c: _collection_lastmod(hubs[c]) for c in indexed_hubs},
        tag_lastmod={s: _collection_lastmod(tags[s]) for s in indexed_tags},
    )
    (SITE_DIR / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8")
    _assert_sitemap_matches_disk(sitemap_xml)
    _assert_no_dead_internal_links()
    print(f"  Generated sitemap → site/sitemap.xml")

    (SITE_DIR / "_redirects").write_text(
        _generate_redirects(retired_targets), encoding="utf-8"
    )
    print(f"  Generated redirects → site/_redirects")

    candidates = _tag_synonym_candidates(all_weeks)
    if candidates:
        print(f"  Check     {len(candidates)} possible tag synonym group(s) — "
              "add real ones to TAG_ALIASES:")
        for group in candidates:
            print(f"              {' / '.join(group)}")

    (SITE_DIR / "llms.txt").write_text(
        _generate_llms_txt(all_weeks, SITE_URL, SITE_NAME, SITE_TAGLINE, hubs, tags),
        encoding="utf-8",
    )
    print(f"  Generated llms.txt → site/llms.txt")

    (SITE_DIR / "feed.xml").write_text(
        _generate_rss(all_weeks, SITE_URL, SITE_NAME, SITE_TAGLINE), encoding="utf-8"
    )
    print(f"  Generated feed    → site/feed.xml")

    # ------------------------------------------------------------------
    # Phase 6: persist the manifest
    # ------------------------------------------------------------------
    _save_manifest(manifest)
    print(f"  Saved     manifest → {MANIFEST_PATH.relative_to(HERE)}")

    total   = len(all_weeks)
    skipped = total - len(render_set)
    print(
        f"\nBuild complete: {rendered_count} week(s) rendered, "
        f"{skipped} skipped, {total} total in archive."
    )
    if rendered_count == 0 and skipped == total:
        print("Everything is up to date.")
    else:
        print("Open: site/index.html")


if __name__ == "__main__":
    build()
