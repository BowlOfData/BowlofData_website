// Shared server-side rendering for the dynamic pages (week / topic / tag / archive).
//
// This mirrors the Jinja templates in templates/*.html so the functions emit the
// SAME markup the Python static build produced. If the header/footer/nav in
// templates/base.html changes, mirror it in `shell()` below.

// ---------------------------------------------------------------------------
// Site constants (mirror build.py)
// ---------------------------------------------------------------------------
export const SITE_NAME = "Bowl of Data";
export const SITE_TAGLINE = "A weekly digest of the most relevant tech stories";
export const SITE_URL = "https://bowlofdata.net";
export const PODCAST_URL = "https://open.spotify.com/show/033Mqus9YAIssepHakRIIk";
export const SUBSTACK_URL = "https://bowlofdata.substack.com/";
export const OG_IMAGE = `${SITE_URL}/imgs/bowl.png`;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// Matches Jinja2 / markupsafe autoescape exactly.
export function esc(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/'/g, "&#39;")
    .replace(/"/g, "&#34;");
}

// Exact port of build.py:_slugify — keep in sync so tag URLs match.
export function slugify(text) {
  let slug = String(text || "").toLowerCase().trim();
  slug = slug.replace(/[^\w\s-]/g, "");   // \w in JS is [A-Za-z0-9_], same as Python re \w on ASCII
  slug = slug.replace(/[\s_]+/g, "-");
  slug = slug.replace(/-+/g, "-");
  return slug.replace(/^-+|-+$/g, "");
}

const plural = (n) => (n !== 1 ? "s" : "");

// YYYY-MM-DD (UTC) from an epoch-seconds mtime, matching Python's
// datetime.fromtimestamp(mtime, tz=utc).strftime("%Y-%m-%d").
export function dateFromMtime(mtime) {
  if (!mtime) return null;
  return new Date(Number(mtime) * 1000).toISOString().slice(0, 10);
}

// ---------------------------------------------------------------------------
// JSON-LD (ports of build.py:_make_*_jsonld).
// pyJson mirrors Python's json.dumps(obj, ensure_ascii=False): (', ', ': ')
// separators and literal (non-\u-escaped) non-ASCII — so the emitted blocks are
// byte-identical to what the Python build produced.
// ---------------------------------------------------------------------------

function pyJson(v) {
  if (v === null || v === undefined) return "null";
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  if (typeof v === "string") return JSON.stringify(v);
  if (Array.isArray(v)) return "[" + v.map(pyJson).join(", ") + "]";
  const parts = Object.entries(v).map(([k, val]) => JSON.stringify(k) + ": " + pyJson(val));
  return "{" + parts.join(", ") + "}";
}

// WebSite JSON-LD — used on the archive page (matches build.py:_make_website_jsonld).
export const WEBSITE_JSONLD = pyJson({
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: SITE_NAME,
  description: SITE_TAGLINE,
  url: SITE_URL,
});

export const ORGANIZATION_JSONLD = pyJson({
  "@context": "https://schema.org",
  "@type": "Organization",
  name: SITE_NAME,
  description: SITE_TAGLINE,
  url: SITE_URL,
  logo: `${SITE_URL}/imgs/logo.png`,
  sameAs: [
    "https://bowlofdata.substack.com/",
    "https://www.instagram.com/bowl_of_data",
    PODCAST_URL,
  ],
});

function publisherNode() {
  return {
    "@type": "Organization",
    name: SITE_NAME,
    url: SITE_URL,
    logo: { "@type": "ImageObject", url: `${SITE_URL}/imgs/logo.png` },
  };
}

// w: { week, year, label, href, articleCount, sourceMtime, articles: [{title,url,slug,short_summary,published}] }
export function weekJsonld(w) {
  const count = w.articleCount;
  const weekUrl = `${SITE_URL}/${w.href}`;
  const publisher = publisherNode();
  const weekDate = dateFromMtime(w.sourceMtime);
  const items = w.articles.map((a, i) => {
    const node = {
      "@type": "NewsArticle",
      headline: a.title,
      url: a.url || `${weekUrl}#${a.slug}`,
      image: OG_IMAGE,
      publisher,
      author: { "@type": "Organization", name: SITE_NAME, url: SITE_URL },
    };
    if (a.short_summary) node.description = a.short_summary;
    if (a.published) node.datePublished = a.published;
    else if (weekDate) node.datePublished = weekDate;
    return { "@type": "ListItem", position: i + 1, item: node };
  });
  const page = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: `${w.label} · ${SITE_NAME}`,
    description:
      `${count} article${plural(count)} curated this week ` +
      "covering AI, cybersecurity, blockchain and engineering.",
    url: weekUrl,
    publisher,
    mainEntity: { "@type": "ItemList", numberOfItems: count, itemListElement: items },
  };
  if (weekDate) {
    page.datePublished = weekDate;
    page.dateModified = weekDate;
  }
  return pyJson(page);
}

// items: [{ title, week_href, slug, short_summary, date }]
export function collectionJsonld(name, description, url, items) {
  const publisher = publisherNode();
  const listItems = items.map((it, i) => {
    const node = {
      "@type": "NewsArticle",
      headline: it.title,
      url: `${SITE_URL}/${it.week_href}#${it.slug}`,
      image: OG_IMAGE,
      publisher,
      author: { "@type": "Organization", name: SITE_NAME, url: SITE_URL },
    };
    if (it.short_summary) node.description = it.short_summary;
    if (it.date) node.datePublished = it.date;
    return { "@type": "ListItem", position: i + 1, item: node };
  });
  return pyJson({
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name,
    description,
    url,
    publisher,
    mainEntity: { "@type": "ItemList", numberOfItems: items.length, itemListElement: listItems },
  });
}

// crumbs: [[name, url|null], ...]
export function breadcrumbJsonld(crumbs) {
  const elements = crumbs.map(([name, url], i) => {
    const el = { "@type": "ListItem", position: i + 1, name };
    if (url) el.item = url;
    return el;
  });
  return pyJson({
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: elements,
  });
}

// ---------------------------------------------------------------------------
// Shell (port of templates/base.html)
// ---------------------------------------------------------------------------
// nav hrefs are relative; `prefix` is "" for root pages (archive) or "../" for
// pages nested one level deep (week/topic/tag).
function nav(prefix, currentPage) {
  // The Jinja templates leave a literal space before the conditional attr
  // (`class="nav-link" {% if %}…{% endif %}>`), so the space lives in the markup
  // below and these helpers emit only the attribute (or nothing).
  const cur = (p) => (currentPage === p ? 'aria-current="page"' : "");
  const aboutActive = ["about", "team", "contact"].includes(currentPage) ? 'data-active="true"' : "";
  return `
  <header class="site-header">
    <div class="header-inner">
      <a href="${prefix}index.html" class="header-brand">
        <img src="${prefix}imgs/logo.png" alt="${esc(SITE_NAME)} logo" class="header-logo">
        <div class="header-text">
          <span class="header-site-name">${esc(SITE_NAME)}</span>
          <span class="header-tagline">${esc(SITE_TAGLINE)}</span>
        </div>
      </a>
      <button class="menu-toggle" aria-label="Toggle navigation" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
      <nav class="header-nav">
        <a href="${prefix}index.html" class="nav-link" ${cur("home")}>Home</a>
        <a href="${prefix}archive.html" class="nav-link" ${cur("archive")}>Archive</a>
        <a href="${prefix}topics.html" class="nav-link" ${cur("topics")}>Topics</a>
        <a href="${prefix}services.html" class="nav-link nav-link--services" ${cur("services")}>Services</a>
        <div class="nav-more-group">
          <button class="nav-more-btn" aria-expanded="false" aria-haspopup="true" ${aboutActive}>
            About
            <svg class="nav-more-chevron" width="10" height="6" viewBox="0 0 10 6" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 1l4 4 4-4"/></svg>
          </button>
          <div class="nav-more-panel">
            <a href="${prefix}about.html" class="nav-link" ${cur("about")}>About</a>
            <a href="${prefix}team.html" class="nav-link" ${cur("team")}>Team</a>
            <a href="${prefix}contact.html" class="nav-link" ${cur("contact")}>Contact</a>
            <a href="${PODCAST_URL}" class="nav-link nav-link--podcast" target="_blank" rel="noopener">
              <svg class="nav-podcast-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141 4.32-1.32 9.719-.66 13.5 1.62.32.24.5.72.24 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.6.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.42 1.56-.299.421-1.02.599-1.559.3z"/>
              </svg>
              Podcast
            </a>
          </div>
        </div>
        <a href="https://bowlofdata.substack.com/" class="nav-subscribe" target="_blank" rel="noopener">Subscribe</a>
      </nav>
    </div>
  </header>`;
}

const FOOTER = `
  <footer class="site-footer">
    <div class="footer-inner">
      <img src="{LOGO}" alt="${esc(SITE_NAME)}" class="footer-logo">
      <div class="footer-text">
        <p class="footer-name">${esc(SITE_NAME)}</p>
        <p class="footer-sub">${esc(SITE_TAGLINE)}</p>
        <p class="footer-authored">Curated by Maki &amp; reviewed by the ${esc(SITE_NAME)} team.</p>
      </div>
      <div class="footer-social">
        <a href="https://www.instagram.com/bowl_of_data" class="footer-social-link" target="_blank" rel="noopener" aria-label="Instagram">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
            <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>
            <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/>
          </svg>
        </a>
        <a href="https://bowlofdata.substack.com/" class="footer-social-link" target="_blank" rel="noopener" aria-label="Subscribe on Substack">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M22.539 8.242H1.46V5.406h21.08v2.836zM1.46 10.812V24L12 18.11 22.54 24V10.812H1.46zM22.54 0H1.46v2.836h21.08V0z"/>
          </svg>
        </a>
        <a href="${PODCAST_URL}" class="footer-social-link" target="_blank" rel="noopener" aria-label="Listen on Spotify">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141 4.32-1.32 9.719-.66 13.5 1.62.32.24.5.72.24 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.6.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.42 1.56-.299.421-1.02.599-1.559.3z"/>
        </svg>
        </a>
      </div>
      <p class="footer-credit">
        Powered by
        <a href="https://github.com/bowlofdata/maki" target="_blank" rel="noopener">Maki</a>
      </p>
    </div>
  </footer>`;

const SCRIPTS = `
  <script>
    document.documentElement.classList.add('js-anim');
    (function () {
      var btn      = document.querySelector('.menu-toggle');
      var nav      = document.querySelector('.header-nav');
      var moreBtn  = document.querySelector('.nav-more-btn');
      var morePanel = document.querySelector('.nav-more-panel');

      // Hamburger toggle
      if (btn && nav) {
        btn.addEventListener('click', function () {
          var open = nav.classList.toggle('is-open');
          btn.setAttribute('aria-expanded', String(open));
        });
      }

      // More dropdown toggle
      if (moreBtn && morePanel) {
        moreBtn.addEventListener('click', function (e) {
          e.stopPropagation();
          var open = morePanel.classList.toggle('is-open');
          moreBtn.setAttribute('aria-expanded', String(open));
        });
        document.addEventListener('keydown', function (e) {
          if (e.key === 'Escape' && morePanel.classList.contains('is-open')) {
            morePanel.classList.remove('is-open');
            moreBtn.setAttribute('aria-expanded', 'false');
            moreBtn.focus();
          }
        });
      }

      // Close both on outside click
      document.addEventListener('click', function (e) {
        if (!e.target.closest('.header-inner') && nav && nav.classList.contains('is-open')) {
          nav.classList.remove('is-open');
          btn.setAttribute('aria-expanded', 'false');
        }
        if (!e.target.closest('.nav-more-group') && morePanel && morePanel.classList.contains('is-open')) {
          morePanel.classList.remove('is-open');
          moreBtn.setAttribute('aria-expanded', 'false');
        }
      });
    })();

    // Cookie consent
    (function () {
      var banner = document.getElementById('cookie-banner');
      if (!banner) return;
      if (!localStorage.getItem('cookie-consent')) {
        banner.classList.add('is-visible');
      }
      document.getElementById('cookie-accept').addEventListener('click', function () {
        localStorage.setItem('cookie-consent', 'accepted');
        banner.classList.remove('is-visible');
      });
      document.getElementById('cookie-decline').addEventListener('click', function () {
        localStorage.setItem('cookie-consent', 'declined');
        banner.classList.remove('is-visible');
      });
    })();
  </script>`;

const COOKIE_BANNER = `
  <!-- Cookie consent banner -->
  <div id="cookie-banner" class="cookie-banner" role="dialog" aria-label="Cookie consent" aria-live="polite">
    <div class="cookie-banner-inner">
      <p class="cookie-banner-text">
        We use cookies and similar technologies — including Google Fonts — to operate this site.
        No advertising or tracking cookies are used.
        By clicking <strong>Accept</strong> you agree to our use of these technologies.
        <a href="https://policies.google.com/privacy" class="cookie-banner-link" target="_blank" rel="noopener">Google's privacy policy</a>.
      </p>
      <div class="cookie-banner-actions">
        <button id="cookie-accept" class="cookie-btn cookie-btn-accept">Accept</button>
        <button id="cookie-decline" class="cookie-btn cookie-btn-decline">Decline</button>
      </div>
    </div>
  </div>`;

// opts: { title, description, ogType, url, prefix, currentPage, jsonld: [strings], body }
export function shell(opts) {
  const { title, description, ogType = "website", url, prefix, currentPage, jsonld = [], body } = opts;
  const t = esc(title);
  const d = esc(description);
  const cssPath = `${prefix}static/style.css`;
  const logoPath = `${prefix}imgs/logo.png`;
  const jsonldBlocks = [ORGANIZATION_JSONLD, ...jsonld]
    .map((s) => `  <script type="application/ld+json">${s}</script>`)
    .join("\n");

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${t}</title>
  <meta name="description" content="${d}">
  <meta name="author" content="${esc(SITE_NAME)} team">
  <link rel="canonical" href="${esc(url)}">
  <link rel="icon" type="image/png" href="${SITE_URL}/imgs/logo.png">
  <link rel="apple-touch-icon" href="${SITE_URL}/imgs/logo.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;700;800&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="${cssPath}">
  <!-- Open Graph -->
  <meta property="og:site_name" content="${esc(SITE_NAME)}">
  <meta property="og:type" content="${ogType}">
  <meta property="og:title" content="${t}">
  <meta property="og:description" content="${d}">
  <meta property="og:image" content="${SITE_URL}/imgs/bowl.png">
  <meta property="og:image:width" content="2560">
  <meta property="og:image:height" content="1440">
  <meta property="og:image:alt" content="${esc(SITE_NAME)} — weekly tech newsletter">
  <meta property="og:url" content="${esc(url)}">
  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="${t}">
  <meta name="twitter:description" content="${d}">
  <meta name="twitter:image" content="${SITE_URL}/imgs/bowl.png">
  <link rel="alternate" type="application/rss+xml" title="${esc(SITE_NAME)} RSS Feed" href="${SITE_URL}/feed.xml">
${jsonldBlocks}
</head>
<body>
${nav(prefix, currentPage)}

  <main class="main-content">
${body}
  </main>
${FOOTER.replace(/\{LOGO\}/g, logoPath)}
${COOKIE_BANNER}
${SCRIPTS}
</body>
</html>`;
}

// ---------------------------------------------------------------------------
// Subscribe CTA (port of templates/_subscribe.html)
// ---------------------------------------------------------------------------
function subscribeCta(ctx) {
  const href = `${SUBSTACK_URL}?utm_source=bowlofdata&amp;utm_medium=site&amp;utm_campaign=${ctx || "inline"}`;
  return `
<section class="subscribe-cta" aria-label="Subscribe to Bowl of Data">
  <div class="subscribe-cta-inner">
    <p class="subscribe-cta-kicker">Free weekly digest</p>
    <h2 class="subscribe-cta-title">Get next Saturday&rsquo;s issue in your inbox</h2>
    <p class="subscribe-cta-sub">
      The week&rsquo;s most relevant AI, security, blockchain, and engineering stories —
      curated, summarised, and reviewed by humans. No spam, unsubscribe anytime.
    </p>
    <a href="${href}"
       class="cta-primary" target="_blank" rel="noopener">Subscribe — it&rsquo;s free</a>
  </div>
</section>`;
}

// ---------------------------------------------------------------------------
// Article/paper card (shared by week.html articles + papers)
// ---------------------------------------------------------------------------
function articleCard(a, index, numberLabel, readMoreLabel, linkableTags) {
  const paras = a.long_resume_paragraphs || [];
  const techs = a.technologies || [];
  const tagsHtml = techs.length
    ? `<div class="article-tags">
            ${techs
              .map((tech) => {
                const tslug = slugify(tech);
                return linkableTags.has(tslug)
                  ? `<a class="tag tag--link" href="../tag/${tslug}.html">${esc(tech)}</a>`
                  : `<span class="tag">${esc(tech)}</span>`;
              })
              .join("\n            ")}
          </div>`
    : "";
  return `      <article class="article-card" id="${esc(a.slug)}">

        <div class="article-card-top">
          <p class="article-number">${numberLabel} ${index}</p>
          <h2 class="article-title">
            ${a.url
              ? `<a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title)}</a>`
              : `${esc(a.title)}`}
          </h2>
          <div class="article-meta">
            ${a.category_label
              ? `<a class="beat-badge beat-badge--${esc(a.category)}" href="../topic/${esc(a.category)}.html">${esc(a.category_label)}</a>`
              : ""}
            ${a.source ? `<span class="article-source">${esc(a.source)}</span>` : ""}
          </div>
        </div>

        <div class="article-card-body">
          ${a.main_topic ? `<p class="article-topic">${esc(a.main_topic)}</p>` : ""}
          ${a.short_summary
            ? `<div class="tldr-box">
            <p class="tldr-label">TL;DR</p>
            <p class="tldr-text">${esc(a.short_summary)}</p>
          </div>`
            : ""}
          ${paras.length
            ? `<div class="long-resume">
            ${paras.map((p) => `<p>${esc(p)}</p>`).join("\n            ")}
          </div>`
            : ""}
        </div>

        <div class="article-card-footer">
          ${tagsHtml}
          ${a.url ? `<a class="read-more" href="${esc(a.url)}" target="_blank" rel="noopener">${readMoreLabel} →</a>` : ""}
        </div>

      </article>`;
}

function releaseCard(item) {
  const feats = item.key_features || [];
  return `        <article class="release-card" id="${esc(item.slug)}">

          <div class="release-card-top">
            <div class="release-meta-row">
              <span class="release-provider-tag">${esc(item.provider)}</span>
              ${item.release_date && item.release_date !== "recent"
                ? `<span class="release-date-pill">${esc(item.release_date)}</span>`
                : ""}
            </div>
            <h3 class="release-name">
              ${item.url
                ? `<a href="${esc(item.url)}" target="_blank" rel="noopener">${esc(item.model_name)}</a>`
                : `${esc(item.model_name)}`}
            </h3>
          </div>

          <div class="release-card-body">
            ${item.summary ? `<p class="release-summary">${esc(item.summary)}</p>` : ""}
            ${feats.length
              ? `<ul class="release-features">
              ${feats.map((f) => `<li>${esc(f)}</li>`).join("\n              ")}
            </ul>`
              : ""}
          </div>

          ${item.url
            ? `<div class="release-card-footer">
            <a href="${esc(item.url)}" class="release-read-link" target="_blank" rel="noopener">Read announcement →</a>
          </div>`
            : ""}

        </article>`;
}

// ---------------------------------------------------------------------------
// week page (port of templates/week.html)
// ---------------------------------------------------------------------------
// w: { week, year, label, href, sourceMtime, articles[], papers[], releases[],
//      prevWeek:{href,label}|null, nextWeek:{href,label}|null }
export function renderWeek(w, linkableTags) {
  const week2 = String(w.week).padStart(2, "0");
  const articles = w.articles || [];
  const papers = w.papers || [];
  const releases = w.releases || [];

  let meta = `${articles.length} article${plural(articles.length)}`;
  if (releases.length) meta += ` · ${releases.length} model release${plural(releases.length)}`;
  if (papers.length) meta += ` · ${papers.length} paper${plural(papers.length)}`;

  const navHeader =
    w.prevWeek || w.nextWeek
      ? `    <div class="week-nav week-nav--header">
      ${w.prevWeek ? `<a href="../${w.prevWeek.href}" class="week-nav-btn week-nav-older">← ${esc(w.prevWeek.label)}</a>` : "<span></span>"}
      ${w.nextWeek ? `<a href="../${w.nextWeek.href}" class="week-nav-btn week-nav-newer">${esc(w.nextWeek.label)} →</a>` : "<span></span>"}
    </div>`
      : "";

  const releasesSection = releases.length
    ? `
<section class="releases-section">

  <div class="releases-header">
    <div class="releases-header-inner">
      <div class="releases-header-text">
        <h2 class="releases-title">AI Model Releases</h2>
        <p class="releases-sub">New models and updates from major AI providers this week</p>
      </div>
      <span class="releases-badge">This Week</span>
    </div>
  </div>

  <div class="releases-body">
    <div class="releases-body-inner">
      <div class="releases-grid">
${releases.map(releaseCard).join("\n")}
      </div>
    </div>
  </div>

</section>`
    : "";

  const papersSection = papers.length
    ? `
<section class="papers-section">

  <div class="releases-header">
    <div class="releases-header-inner">
      <div class="releases-header-text">
        <h2 class="releases-title">Research Papers</h2>
        <p class="releases-sub">Selected arXiv and HuggingFace papers this week</p>
      </div>
      <span class="releases-badge papers-badge">This Week</span>
    </div>
  </div>

  <div class="releases-body">
    <div class="article-section">
      <div class="article-list">
${papers.map((p, i) => articleCard(p, i + 1, "Paper", "Read paper", linkableTags)).join("\n")}
      </div>
    </div>
  </div>

</section>`
    : "";

  const articlesBlock = articles.length
    ? `
    <div class="article-list">
${articles.map((a, i) => articleCard(a, i + 1, "Article", "Read full article", linkableTags)).join("\n")}
    </div>

    <div class="week-nav week-nav-bottom-bar">
      ${w.prevWeek ? `<a href="../${w.prevWeek.href}" class="week-nav-btn week-nav-older">← ${esc(w.prevWeek.label)}</a>` : "<span></span>"}
      <a href="../archive.html" class="week-nav-btn week-nav-archive">All issues</a>
      ${w.nextWeek ? `<a href="../${w.nextWeek.href}" class="week-nav-btn week-nav-newer">${esc(w.nextWeek.label)} →</a>` : "<span></span>"}
    </div>
`
    : `
    <p class="empty-state">No articles in this issue.</p>
`;

  const body = `<div class="week-header">
  <div class="week-header-inner">
    <a href="../archive.html" class="back-link">← All issues</a>
    <h1 class="week-title">
      Week <span class="week-title-accent">${week2}</span> · ${w.year}
    </h1>
    <p class="week-meta">${meta}</p>
${navHeader}
  </div>
</div>
${releasesSection}
${papersSection}
<section class="news-section">

  <div class="releases-header news-section-band">
    <div class="releases-header-inner">
      <div class="releases-header-text">
        <h2 class="releases-title">This Week in Tech</h2>
        <p class="releases-sub">Top stories curated from across the web this week</p>
      </div>
      <span class="releases-badge news-badge">This Week</span>
    </div>
  </div>

  <div class="article-section">
${articlesBlock}
  </div>

</section>
${subscribeCta("week")}`;

  return shell({
    title: `${w.label} · ${SITE_NAME}`,
    description: `${articles.length} article${plural(articles.length)} curated this week: AI, cybersecurity, blockchain and engineering.`,
    ogType: "article",
    url: `${SITE_URL}/week/${week2}_${w.year}.html`,
    prefix: "../",
    currentPage: null, // week pages set no active nav item (matches the Python build)
    jsonld: [
      weekJsonld({
        week: w.week, year: w.year, label: w.label, href: w.href,
        articleCount: articles.length, sourceMtime: w.sourceMtime, articles,
      }),
      breadcrumbJsonld([
        [SITE_NAME, `${SITE_URL}/`],
        ["Archive", `${SITE_URL}/archive.html`],
        [w.label, `${SITE_URL}/${w.href}`],
      ]),
    ],
    body,
  });
}

// ---------------------------------------------------------------------------
// collection page — topic hub and tag page (port of templates/collection.html)
// ---------------------------------------------------------------------------
// c: { pageTitle, kicker, h1, intro, ogDesc, canonicalUrl, count,
//      groups:[{label, week_href, entries:[{title,slug,short_summary,url,source,category,category_label,week_href}]}],
//      relatedTopics:[{slug,label}]|null, relatedTags:[{slug,name,count}]|null,
//      flatItems (for jsonld), breadcrumb:[[name,url]] }
export function renderCollection(c) {
  const issueCount = c.groups.length;

  const relatedTopicsHtml = c.relatedTopics
    ? `
    <div class="collection-chips">
      ${c.relatedTopics
        .map((t) => `<a href="../topic/${esc(t.slug)}.html" class="chip chip--beat">${esc(t.label)}</a>`)
        .join("\n      ")}
    </div>`
    : "";

  const relatedTagsHtml = c.relatedTags
    ? `
    <div class="collection-chips">
      ${c.relatedTags
        .map((t) => `<a href="../tag/${esc(t.slug)}.html" class="chip">${esc(t.name)} <span>${t.count}</span></a>`)
        .join("\n      ")}
    </div>`
    : "";

  const groupsHtml = c.groups
    .map(
      (g) => `  <section class="collection-group">
    <div class="collection-group-head">
      <h2 class="collection-group-title">${esc(g.label)}</h2>
      <a href="../${g.week_href}" class="collection-group-link">Read the issue →</a>
    </div>
    <ul class="collection-list">
${g.entries
  .map(
    (it) => `      <li class="collection-item">
        <a href="../${it.week_href}#${esc(it.slug)}" class="collection-item-title">${esc(it.title)}</a>
        ${it.short_summary ? `<p class="collection-item-sum">${esc(it.short_summary)}</p>` : ""}
        <div class="collection-item-meta">
          <span class="chip chip--beat">${esc(it.category_label)}</span>
          ${it.source ? `<span class="collection-item-src">${esc(it.source)}</span>` : ""}
          ${it.url ? `<a href="${esc(it.url)}" target="_blank" rel="noopener" class="collection-item-ext">Source ↗</a>` : ""}
        </div>
      </li>`
  )
  .join("\n")}
    </ul>
  </section>`
    )
    .join("\n");

  const body = `<div class="collection-header">
  <div class="collection-header-inner">
    <a href="../topics.html" class="back-link">← All topics</a>
    <p class="collection-kicker">${esc(c.kicker)}</p>
    <h1 class="collection-title">${esc(c.h1)}</h1>
    <p class="collection-intro">${esc(c.intro)}</p>
    <p class="collection-meta">${c.count} item${plural(c.count)} · ${issueCount} issue${plural(issueCount)}</p>
${relatedTopicsHtml}${relatedTagsHtml}
  </div>
</div>

<div class="collection-body">
${groupsHtml}
</div>
${subscribeCta("topic")}`;

  return shell({
    title: c.pageTitle,
    description: c.ogDesc,
    ogType: "article",
    url: c.canonicalUrl,
    prefix: "../",
    currentPage: "topics",
    jsonld: [
      collectionJsonld(c.jsonldName, c.ogDesc, c.canonicalUrl, c.flatItems),
      breadcrumbJsonld(c.breadcrumb),
    ],
    body,
  });
}

// ---------------------------------------------------------------------------
// archive (port of templates/archive.html)
// ---------------------------------------------------------------------------
// weeksByYear: [{year, count, months:[{month_name, weeks:[{href,label,article_count,preview_titles[]}]}]}]
export function renderArchive(weeksByYear, totalCount) {
  const yearNav =
    weeksByYear.length > 1
      ? `<div class="archive-year-nav">
  <div class="archive-year-nav-inner">
    <span class="archive-year-nav-label">Jump to</span>
    ${weeksByYear.map((yg) => `<a href="#year-${yg.year}" class="archive-year-pill">${yg.year}</a>`).join("\n    ")}
  </div>
</div>`
      : "";

  let isFirst = true;
  const bodyInner = weeksByYear.length
    ? `
${yearNav}

<div class="archive-body">
${weeksByYear
  .map(
    (yg) => `  <section class="archive-year-section" id="year-${yg.year}">

    <div class="archive-year-band">
      <div class="archive-year-band-inner">
        <span class="archive-year-label">${yg.year}</span>
        <span class="archive-year-count">${yg.count} issue${plural(yg.count)}</span>
      </div>
    </div>

${yg.months
  .map(
    (mg) => `    <div class="archive-month-section">
      <div class="archive-month-header">
        <span class="archive-month-name">${esc(mg.month_name)}</span>
        <span class="archive-month-count">${mg.weeks.length} issue${plural(mg.weeks.length)}</span>
      </div>
      <div class="week-grid">
${mg.weeks
  .map((wk) => {
    const latest = isFirst;
    isFirst = false;
    const previews = wk.preview_titles && wk.preview_titles.length
      ? `
          <ul class="week-card-preview">
            ${wk.preview_titles.map((t) => `<li>${esc(t)}</li>`).join("\n            ")}
          </ul>`
      : "";
    return `        <a class="week-card${latest ? " week-card-latest" : ""}" href="${wk.href}">
          ${latest ? '<span class="week-card-badge">Latest</span>' : ""}
          <div class="week-card-label">${esc(wk.label)}</div>
          <div class="week-card-count">${wk.article_count} articles</div>${previews}
        </a>`;
  })
  .join("\n")}
      </div>
    </div>`
  )
  .join("\n")}

  </section>`
  )
  .join("\n")}
</div>
`
    : `
<div class="section">
  <p class="empty-state">No newsletters found yet. Run the Maki pipeline to generate the first issue.</p>
</div>`;

  const statHtml = totalCount
    ? `
    <div class="archive-header-stat">
      <span class="archive-stat-num">${totalCount}</span>
      <span class="archive-stat-label">issue${plural(totalCount)}</span>
    </div>`
    : "";

  const body = `<div class="archive-header">
  <div class="archive-header-inner">
    <div class="archive-header-text">
      <h1 class="archive-title">All issues</h1>
      <p class="archive-sub">Every weekly digest, from the first bowl to the latest.</p>
    </div>${statHtml}
  </div>
</div>
${bodyInner}`;

  return shell({
    title: `Archive · ${SITE_NAME}`,
    description:
      "Browse every past issue of Bowl of Data, the weekly tech newsletter covering AI, cybersecurity, blockchain, and engineering.",
    ogType: "website",
    url: `${SITE_URL}/archive.html`,
    prefix: "",
    currentPage: "archive",
    jsonld: [WEBSITE_JSONLD],
    body,
  });
}
