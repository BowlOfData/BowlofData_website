// GET /week/WW_YYYY.html  → full week issue, server-rendered from Neon.
import { sql, html, notFound, slugFromPath, keptTagSlugs } from "./_shared/db.mjs";
import { renderWeek } from "./_shared/render.mjs";

export default async (req) => {
  const slug = slugFromPath(req.url);
  const m = slug.match(/^(\d{1,2})_(\d{4})$/);
  if (!m) return notFound();
  const week = parseInt(m[1], 10);
  const year = parseInt(m[2], 10);

  const weeks = await sql`
    SELECT week, year, label, href, source_mtime
    FROM bowl_of_data.weeks WHERE week = ${week} AND year = ${year}
  `;
  if (weeks.length === 0) return notFound();
  const wk = weeks[0];

  const [items, releases, prevRows, nextRows, linkable] = await Promise.all([
    sql`
      SELECT kind, title, slug, url, source, published, short_summary,
             long_resume_paragraphs, main_topic, technologies, category, category_label
      FROM bowl_of_data.items WHERE week = ${week} AND year = ${year}
      ORDER BY kind, position
    `,
    sql`
      SELECT slug, provider, model_name, release_date, summary, url, key_features
      FROM bowl_of_data.releases WHERE week = ${week} AND year = ${year}
      ORDER BY position
    `,
    sql`
      SELECT week, year, label, href FROM bowl_of_data.weeks
      WHERE (year, week) < (${year}, ${week})
      ORDER BY year DESC, week DESC LIMIT 1
    `,
    sql`
      SELECT week, year, label, href FROM bowl_of_data.weeks
      WHERE (year, week) > (${year}, ${week})
      ORDER BY year ASC, week ASC LIMIT 1
    `,
    keptTagSlugs(),
  ]);

  const page = renderWeek(
    {
      week: wk.week,
      year: wk.year,
      label: wk.label,
      href: wk.href,
      sourceMtime: wk.source_mtime,
      articles: items.filter((i) => i.kind === "article"),
      papers: items.filter((i) => i.kind === "paper"),
      releases,
      prevWeek: prevRows[0] || null, // older issue
      nextWeek: nextRows[0] || null, // newer issue
    },
    linkable
  );

  return html(page);
};
