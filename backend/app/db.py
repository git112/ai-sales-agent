from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path

from app.core.config import settings

log = logging.getLogger("lumina.db")

LIST_COLLECTIONS = [
    "users",
    "workspaces",
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

_lock = threading.RLock()
_conn: sqlite3.Connection | None = None
_active = False
_failed = False


def db_path() -> Path:
    path = Path(settings.sqlite_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent / path
    return path


def sqlite_active() -> bool:
    return _active and not _failed


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        raise RuntimeError("SQLite is not initialized")
    _enable_foreign_keys(_conn)
    return _conn


def close_conn() -> None:
    global _conn, _active
    with _lock:
        if _conn is not None:
            _conn.close()
            _conn = None
        _active = False


def _enable_foreign_keys(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False, timeout=15)
    conn.row_factory = sqlite3.Row
    _enable_foreign_keys(conn)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS _meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics (
          workspace_id TEXT PRIMARY KEY,
          payload TEXT NOT NULL
        )
        """
    )
    ddl = """
        CREATE TABLE IF NOT EXISTS {name} (
          id TEXT PRIMARY KEY,
          workspace_id TEXT,
          email TEXT,
          status TEXT,
          lead_id TEXT,
          campaign_id TEXT,
          opportunity_id TEXT,
          call_id TEXT,
          created_at TEXT,
          payload TEXT NOT NULL
        )
        """
    # Circular lead.opportunity_id ↔ opportunity.lead_id is stored as IDs in payload/columns
    # but not as FOREIGN KEY constraints, so seed and updates cannot deadlock.
    for name in LIST_COLLECTIONS:
        conn.execute(ddl.format(name=name))
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{name}_ws ON {name}(workspace_id)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{name}_created ON {name}(created_at)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{name}_status ON {name}(status)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{name}_lead ON {name}(lead_id)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{name}_camp ON {name}(campaign_id)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{name}_opp ON {name}(opportunity_id)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{name}_call ON {name}(call_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    conn.commit()


def meta_get(key: str) -> str | None:
    row = get_conn().execute("SELECT value FROM _meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def meta_set(key: str, value: str) -> None:
    get_conn().execute("INSERT OR REPLACE INTO _meta(key, value) VALUES (?, ?)", (key, value))
    get_conn().commit()


def init_db(path: Path | None = None, seed: bool = True) -> bool:
    """Create the DB file/tables. Seed from JSON only on first successful init."""
    global _conn, _active, _failed
    with _lock:
        if _active and _conn is not None and path is None:
            return True
        try:
            target = path or db_path()
            if _conn is not None:
                _conn.close()
                _conn = None
            _conn = _connect(target)
            _create_tables(_conn)
            _active = True
            _failed = False
            if seed and meta_get("seeded") != "1":
                from app.seed import seed_from_json

                seed_from_json()
                meta_set("seeded", "1")
            log.info("SQLite datastore active (%s)", target)
            print("SQLite datastore active", flush=True)
            return True
        except Exception as exc:
            _failed = True
            _active = False
            if _conn is not None:
                try:
                    _conn.close()
                except Exception:
                    pass
                _conn = None
            log.warning("SQLite unavailable — using JSON demo fallback (%s)", exc)
            print("SQLite unavailable — using JSON demo fallback", flush=True)
            return False
