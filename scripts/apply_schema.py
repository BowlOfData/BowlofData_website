"""Apply scripts/schema.sql to the Neon database.

A psql-free way to (idempotently) create the bowl_of_data schema and tables.
Reads NETLIFY_DATABASE_URL from the environment or a local .env.

    python3 scripts/apply_schema.py
"""
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()
url = (
    os.environ.get("NETLIFY_DATABASE_URL")
    or os.environ.get("NETLIFY_DATABASE_URL_UNPOOLED")
    or os.environ.get("DATABASE_URL")
)
if not url:
    raise SystemExit("Set NETLIFY_DATABASE_URL (see .env) before running.")

sql = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
with psycopg.connect(url) as conn:
    conn.execute(sql)
    conn.commit()
print("Schema applied: bowl_of_data schema + weeks / items / releases / item_tags.")
