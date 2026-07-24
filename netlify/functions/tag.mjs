// GET /tag/<slug>.html  → technology tag page, from Neon.
// Mirrors build.py:_collect_tags — only tags with >= 3 items get a page.
import { sql, html, notFound, slugFromPath } from "./_shared/db.mjs";
import { renderCollection, dateFromMtime, SITE_NAME, SITE_URL } from "./_shared/render.mjs";
import { CATEGORY_ORDER, CATEGORY_META } from "./_shared/topics.mjs";

export default async (req) => {
  const slug = slugFromPath(req.url);

  const rows = await sql`
    SELECT i.title, i.slug, i.short_summary, i.url, i.source,
           i.category, i.category_label,
           w.label AS week_label, w.href AS week_href, w.source_mtime,
           it.name AS tag_name
    FROM bowl_of_data.item_tags it
    JOIN bowl_of_data.items i ON i.id = it.item_id
    JOIN bowl_of_data.weeks w ON i.week = w.week AND i.year = w.year
    WHERE it.slug = ${slug}
    ORDER BY w.year DESC, w.week DESC, i.kind, i.position
  `;
  // Fewer than 3 items → no page (matches min_items=3). Return 404.
  if (rows.length < 3) return notFound();

  const name = rows[0].tag_name;
  const count = rows.length;

  const groups = [];
  const flat = [];
  const catsSeen = new Set();
  for (const r of rows) {
    catsSeen.add(r.category);
    const entry = {
      title: r.title,
      slug: r.slug,
      short_summary: r.short_summary,
      url: r.url,
      source: r.source,
      category: r.category,
      category_label: r.category_label,
      week_href: r.week_href,
    };
    if (!groups.length || groups[groups.length - 1].week_href !== r.week_href) {
      groups.push({ label: r.week_label, week_href: r.week_href, entries: [entry] });
    } else {
      groups[groups.length - 1].entries.push(entry);
    }
    flat.push({
      title: r.title, week_href: r.week_href, slug: r.slug,
      short_summary: r.short_summary, date: dateFromMtime(r.source_mtime),
    });
  }

  const categories = CATEGORY_ORDER.filter((c) => catsSeen.has(c)).map((c) => ({
    slug: c,
    label: CATEGORY_META[c].label,
  }));

  const url = `${SITE_URL}/tag/${slug}.html`;
  const ogDesc = `Weekly ${name} coverage curated by ${SITE_NAME} — ${count} items across our tech newsletter issues.`;
  const intro =
    `Every ${name} story we've curated in ${SITE_NAME}, newest issue first — part of ` +
    "our weekly digest across AI, security, blockchain, and engineering.";

  const page = renderCollection({
    pageTitle: `${name} — weekly coverage · ${SITE_NAME}`,
    kicker: "Tag",
    h1: name,
    intro,
    ogDesc,
    canonicalUrl: url,
    count,
    groups,
    relatedTopics: categories,
    relatedTags: null,
    flatItems: flat,
    jsonldName: `${name} · ${SITE_NAME}`,
    breadcrumb: [
      [SITE_NAME, `${SITE_URL}/`],
      ["Topics", `${SITE_URL}/topics.html`],
      [name, url],
    ],
  });

  return html(page);
};
