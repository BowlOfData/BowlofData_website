-- Bowl of Data — Neon Postgres schema (Netlify DB)
-- Apply with:  psql "$NETLIFY_DATABASE_URL" -f scripts/schema.sql
--
-- All objects live in a dedicated `bowl_of_data` schema so the Neon project can be
-- shared with other apps. Every query in build.py and netlify/functions references
-- tables schema-qualified (`bowl_of_data.<table>`); the ALTER ROLE below also sets
-- it as the default search_path for convenience (manual psql, ad-hoc tools).
--
-- Tags and topics are DERIVED, not free-standing tables:
--   topic = items.category ; tags come from item_tags (populated at load time).

CREATE SCHEMA IF NOT EXISTS bowl_of_data;
SET search_path TO bowl_of_data, public;   -- for the CREATE statements in this script

CREATE TABLE IF NOT EXISTS bowl_of_data.weeks (
  week          int              NOT NULL,
  year          int              NOT NULL,
  month         int,
  month_name    text,
  label         text,             -- "Week 30 · 2026"
  href          text,             -- "week/30_2026.html"
  source_mtime  double precision, -- drives sitemap/RSS lastmod + prev/next order
  PRIMARY KEY (week, year)
);

CREATE TABLE IF NOT EXISTS bowl_of_data.items (          -- articles AND papers
  id                     bigserial PRIMARY KEY,
  week                   int  NOT NULL,
  year                   int  NOT NULL,
  kind                   text NOT NULL,     -- 'article' | 'paper'
  position               int  NOT NULL,     -- order within (week, kind)
  title                  text,
  slug                   text,
  url                    text,
  source                 text,
  published              text,
  short_summary          text,
  long_resume            text,
  long_resume_paragraphs jsonb,             -- string[]
  main_topic             text,
  technologies           jsonb,             -- string[] (display names)
  quality_score          numeric,
  category               text,              -- ai|security|blockchain|engineering
  category_label         text,
  FOREIGN KEY (week, year) REFERENCES bowl_of_data.weeks(week, year) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bowl_of_data.releases (       -- AI model releases block on week pages
  id            bigserial PRIMARY KEY,
  week          int  NOT NULL,
  year          int  NOT NULL,
  position      int  NOT NULL,
  slug          text,
  provider      text,
  model_name    text,
  release_date  text,
  summary       text,
  url           text,
  key_features  jsonb,                       -- string[]
  FOREIGN KEY (week, year) REFERENCES bowl_of_data.weeks(week, year) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bowl_of_data.item_tags (      -- one row per (item, technology)
  item_id  bigint NOT NULL REFERENCES bowl_of_data.items(id) ON DELETE CASCADE,
  slug     text   NOT NULL,     -- slugify(technology)
  name     text   NOT NULL      -- canonical display name
);

CREATE INDEX IF NOT EXISTS item_tags_slug_idx ON bowl_of_data.item_tags (slug);
CREATE INDEX IF NOT EXISTS item_tags_item_idx ON bowl_of_data.item_tags (item_id);
CREATE INDEX IF NOT EXISTS items_week_idx      ON bowl_of_data.items (week, year);
CREATE INDEX IF NOT EXISTS items_category_idx  ON bowl_of_data.items (category);

-- Note: build.py and the functions reference every table schema-qualified
-- (bowl_of_data.<table>), so no role search_path default is required. If you use
-- psql/the Neon console interactively, run: SET search_path TO bowl_of_data, public;
