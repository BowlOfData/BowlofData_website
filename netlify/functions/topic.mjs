// GET /topic/<slug>.html  → topic hub (one of the four beats), from Neon.
import { sql, html, notFound, slugFromPath } from "./_shared/db.mjs";
import { renderCollection, dateFromMtime, SITE_NAME, SITE_URL } from "./_shared/render.mjs";
import { CATEGORY_META } from "./_shared/topics.mjs";

export default async (req) => {
  const slug = slugFromPath(req.url);
  const meta = CATEGORY_META[slug];
  if (!meta) return notFound();

  const rows = await sql`
    SELECT i.title, i.slug, i.short_summary, i.url, i.source,
           i.category, i.category_label,
           w.label AS week_label, w.href AS week_href, w.source_mtime
    FROM bowl_of_data.items i
    JOIN bowl_of_data.weeks w ON i.week = w.week AND i.year = w.year
    WHERE i.category = ${slug}
    ORDER BY w.year DESC, w.week DESC, i.kind, i.position
  `;
  if (rows.length === 0) return notFound();

  // Group into per-issue buckets, newest issue first (rows already ordered).
  const groups = [];
  const flat = [];
  for (const r of rows) {
    const date = dateFromMtime(r.source_mtime);
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
    flat.push({ title: r.title, week_href: r.week_href, slug: r.slug, short_summary: r.short_summary, date });
  }

  const relatedRows = await sql`
    SELECT it.slug, max(it.name) AS name, count(*) AS c
    FROM bowl_of_data.item_tags it
    JOIN bowl_of_data.items i ON i.id = it.item_id
    WHERE i.category = ${slug}
      AND it.slug IN (SELECT slug FROM bowl_of_data.item_tags GROUP BY slug HAVING count(*) >= 3)
    GROUP BY it.slug
    ORDER BY c DESC, it.slug
    LIMIT 12
  `;
  const relatedTags = relatedRows.map((r) => ({ slug: r.slug, name: r.name, count: Number(r.c) }));

  const count = rows.length;
  const url = `${SITE_URL}/topic/${slug}.html`;
  const ogDesc = `${meta.h1} coverage from ${SITE_NAME} — ${count} curated items across every weekly issue.`;

  const page = renderCollection({
    pageTitle: `${meta.h1} News · ${SITE_NAME}`,
    kicker: "Topic",
    h1: meta.h1,
    intro: meta.intro,
    ogDesc,
    canonicalUrl: url,
    count,
    groups,
    relatedTopics: null,
    relatedTags,
    flatItems: flat,
    jsonldName: `${meta.h1} · ${SITE_NAME}`,
    breadcrumb: [
      [SITE_NAME, `${SITE_URL}/`],
      ["Topics", `${SITE_URL}/topics.html`],
      [meta.h1, url],
    ],
  });

  return html(page);
};
