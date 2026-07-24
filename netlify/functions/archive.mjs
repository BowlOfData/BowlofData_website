// GET /archive.html  → index of every issue, grouped year → month, from Neon.
import { sql, html } from "./_shared/db.mjs";
import { renderArchive } from "./_shared/render.mjs";

export default async () => {
  const [weekRows, titleRows] = await Promise.all([
    sql`
      SELECT w.week, w.year, w.month, w.month_name, w.label, w.href,
             (SELECT count(*) FROM bowl_of_data.items i
                WHERE i.week = w.week AND i.year = w.year AND i.kind = 'article') AS article_count
      FROM bowl_of_data.weeks w
      ORDER BY w.year DESC, w.week DESC
    `,
    sql`
      SELECT week, year, title FROM bowl_of_data.items
      WHERE kind = 'article'
      ORDER BY year DESC, week DESC, position ASC
    `,
  ]);

  // First 3 article titles per issue → preview list.
  const previews = new Map();
  for (const t of titleRows) {
    const key = `${t.year}_${t.week}`;
    const arr = previews.get(key) || [];
    if (arr.length < 3 && t.title) arr.push(t.title);
    previews.set(key, arr);
  }

  // Group newest-first into year → month buckets.
  const yearMap = new Map();
  for (const w of weekRows) {
    if (!yearMap.has(w.year)) yearMap.set(w.year, new Map());
    const months = yearMap.get(w.year);
    const mo = w.month || 0;
    if (!months.has(mo)) months.set(mo, { month: mo, month_name: w.month_name || "", weeks: [] });
    months.get(mo).weeks.push({
      href: w.href,
      label: w.label,
      article_count: Number(w.article_count),
      preview_titles: previews.get(`${w.year}_${w.week}`) || [],
    });
  }

  const weeksByYear = [...yearMap.entries()]
    .sort((a, b) => b[0] - a[0])
    .map(([year, months]) => {
      const monthList = [...months.values()].sort((a, b) => b.month - a.month);
      const count = monthList.reduce((s, m) => s + m.weeks.length, 0);
      return { year, count, months: monthList };
    });

  return html(renderArchive(weeksByYear, weekRows.length));
};
