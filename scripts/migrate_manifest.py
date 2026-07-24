"""One-time backfill: import every week from the legacy weeks_manifest.json into
Postgres. The maki output directory only keeps recent issues, so history lives
only in the manifest — run this once during the Postgres migration.

    python3 scripts/migrate_manifest.py

Safe to re-run (per-week upsert). After a successful migration + verification,
weeks_manifest.json can be deleted.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build as b

manifest_path = Path(__file__).resolve().parent.parent / "weeks_manifest.json"
if not manifest_path.exists():
    raise SystemExit(f"No manifest found at {manifest_path} — nothing to migrate.")

weeks = json.loads(manifest_path.read_text(encoding="utf-8"))
print(f"Manifest has {len(weeks)} week(s).")

# Backfill classification on any older item that lacks it.
for w in weeks:
    for it in w.get("articles", []) + w.get("papers", []):
        b._ensure_category(it)

conn = b._connect()
try:
    for w in weeks:
        b._upsert_week(conn, w)
        print(f"  Upserted {w['label']} "
              f"({len(w.get('articles', []))} articles, "
              f"{len(w.get('model_releases', []))} releases, "
              f"{len(w.get('papers', []))} papers)")
    b._canonicalize_tag_names(conn)
    conn.commit()
finally:
    conn.close()
print(f"\nMigration complete: {len(weeks)} week(s) in Postgres.")
