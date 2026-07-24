// Shared DB access + response helpers for the dynamic-page functions.
// All content lives in the `bowl_of_data` schema (see scripts/schema.sql); every
// query below references tables schema-qualified.
import { neon } from "@netlify/neon";

// Reads NETLIFY_DATABASE_URL from the environment automatically.
export const sql = neon();

export const HTML_HEADERS = {
  "Content-Type": "text/html; charset=utf-8",
  // Browsers always revalidate; the CDN serves a durable cached copy that is
  // purged on the next deploy (when data changes).
  "Cache-Control": "public, max-age=0, must-revalidate",
  "Netlify-CDN-Cache-Control": "public, durable, s-maxage=86400",
};

export function html(body, status = 200) {
  return new Response(body, { status, headers: HTML_HEADERS });
}

export function notFound() {
  return new Response("Not found", {
    status: 404,
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}

// "…/week/30_2026.html" -> "30_2026" ; "…/tag/nvidia.html" -> "nvidia"
export function slugFromPath(reqUrl) {
  const pathname = new URL(reqUrl).pathname;
  const last = pathname.split("/").pop() || "";
  return decodeURIComponent(last.replace(/\.html$/, ""));
}

// Kept-tag slugs: technologies appearing on >= 3 distinct items (matches
// build.py:_collect_tags min_items=3 and the `linkable_tags` set on week pages).
export async function keptTagSlugs() {
  const rows = await sql`
    SELECT slug FROM bowl_of_data.item_tags GROUP BY slug HAVING count(*) >= 3
  `;
  return new Set(rows.map((r) => r.slug));
}
