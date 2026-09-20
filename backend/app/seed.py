from __future__ import annotations

import json
from pathlib import Path

from app.db import LIST_COLLECTIONS, get_conn
from app.sqlite_store import create_record, write_analytics

SEED_DIR = Path(__file__).resolve().parent.parent / "mock_data"

SEED_ORDER = [
    "workspaces",
    "users",
    "workspace_members",
    "companies",
    "contacts",
    "business_profiles",
    "voice_agents",
    "knowledge_documents",
    "buying_signals",
    "opportunities",
    "leads",
    "campaigns",
    "calls",
    "transcripts",
    "qualifications",
    "tasks",
    "lead_segments",
    "saved_searches",
    "notifications",
    "market_signals",
    "audit_logs",
    "opt_outs",
]


def _load_json(name: str):
    path = SEED_DIR / f"{name}.json"
    if not path.exists():
        return [] if name != "analytics" else {}
    return json.loads(path.read_text(encoding="utf-8"))


def seed_from_json(force: bool = False) -> dict[str, int]:
    """Insert JSON demo records. Existing IDs are skipped (idempotent)."""
    counts: dict[str, int] = {}
    if force:
        conn = get_conn()
        for name in LIST_COLLECTIONS:
            conn.execute(f"DELETE FROM {name}")
        conn.execute("DELETE FROM analytics")
        conn.commit()
    for name in SEED_ORDER:
        rows = _load_json(name)
        if not isinstance(rows, list):
            counts[name] = 0
            continue
        inserted = 0
        for row in rows:
            if not isinstance(row, dict) or not row.get("id"):
                continue
            before = conn_count(name)
            create_record(name, row, ignore_duplicate=True)
            after = conn_count(name)
            if after > before:
                inserted += 1
        counts[name] = inserted if force else conn_count(name)
    analytics = _load_json("analytics")
    if isinstance(analytics, dict) and analytics:
        if force:
            write_analytics(analytics)
        else:
            existing = get_conn().execute("SELECT COUNT(*) AS n FROM analytics").fetchone()["n"]
            if existing == 0:
                write_analytics(analytics)
        counts["analytics"] = get_conn().execute("SELECT COUNT(*) AS n FROM analytics").fetchone()["n"]
    else:
        counts["analytics"] = 0
    return counts


def conn_count(collection: str) -> int:
    return int(get_conn().execute(f"SELECT COUNT(*) AS n FROM {collection}").fetchone()["n"])
