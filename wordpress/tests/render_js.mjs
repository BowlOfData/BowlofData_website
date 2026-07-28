// Render the shared fixture through the live render.mjs and print just the
// article card. Paired with render_php.php by parity.sh.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { renderWeek } from "../../netlify/functions/_shared/render.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const article = JSON.parse(readFileSync(join(here, "fixture-article.json"), "utf8"));

// Only these two clear the >=3 items threshold in the fixture.
const linkable = new Set(["openai", "rust"]);

const html = renderWeek(
  {
    week: 30,
    year: 2026,
    label: "Week 30 · 2026",
    href: "week/30_2026.html",
    sourceMtime: 1785000000,
    articles: [article],
    papers: [],
    releases: [],
    prevWeek: null,
    nextWeek: null,
  },
  linkable
);

const match = html.match(/<article class="article-card"[\s\S]*?<\/article>/);
if (!match) {
  console.error("no article card in renderWeek output");
  process.exit(1);
}
process.stdout.write(match[0]);
