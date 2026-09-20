from __future__ import annotations

import sqlite3
from pathlib import Path

from app.core.config import settings
from app.db import LIST_COLLECTIONS, close_conn, get_conn, init_db
from app.seed import seed_from_json
from app.sqlite_store import count, create_record, delete_record, get_all as sql_all, get_by_id, update_record
from app.store import reset_datastore_state


def _fresh_db(tmp_path: Path):
    reset_datastore_state()
    settings.sqlite_path = str(tmp_path / "sales_agent.db")
    ok = init_db(tmp_path / "sales_agent.db", seed=True)
    assert ok
    from app import store

    store._sqlite_ready = True
    return tmp_path / "sales_agent.db"


def test_sqlite_init_and_tables(tmp_path):
    path = _fresh_db(tmp_path)
    assert path.exists()
    conn = get_conn()
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    for table in LIST_COLLECTIONS + ["analytics", "_meta"]:
        assert table in names
    fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1


def test_sqlite_foreign_keys_pragma_and_enforcement(tmp_path):
    _fresh_db(tmp_path)
    conn = get_conn()
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    conn.execute("CREATE TEMP TABLE parent_fk (id TEXT PRIMARY KEY)")
    conn.execute(
        "CREATE TEMP TABLE child_fk (id TEXT PRIMARY KEY, parent_id TEXT REFERENCES parent_fk(id))"
    )
    conn.execute("INSERT INTO parent_fk(id) VALUES ('p1')")
    try:
        conn.execute("INSERT INTO child_fk(id, parent_id) VALUES ('c1', 'missing')")
        raise AssertionError("foreign keys should reject a missing parent")
    except sqlite3.IntegrityError:
        pass
    conn.execute("INSERT INTO child_fk(id, parent_id) VALUES ('c1', 'p1')")
    row = conn.execute("SELECT parent_id FROM child_fk WHERE id = 'c1'").fetchone()
    assert row[0] == "p1"


def test_sqlite_seed_demo_user_and_abc(tmp_path):
    _fresh_db(tmp_path)
    user = get_by_id("users", "user_001")
    assert user and user["email"] == "demo@example.com"
    opp = get_by_id("opportunities", "opp_abc")
    assert opp and "SharePoint" in (opp.get("title") or "")
    lead = get_by_id("leads", "lead_abc")
    assert lead and lead["company"] == "ABC Technologies"
    assert count("leads") == 4
    assert count("opportunities") == 3
    assert count("campaigns") >= 1
    assert count("calls") >= 1
    assert count("tasks") >= 1
    assert count("notifications") >= 1
    assert count("buying_signals") == 5


def test_sqlite_duplicate_seed(tmp_path):
    _fresh_db(tmp_path)
    before = count("users")
    seed_from_json()
    assert count("users") == before
    seed_from_json()
    assert count("leads") == 4


def test_sqlite_crud(tmp_path):
    _fresh_db(tmp_path)
    rec = create_record(
        "leads",
        {
            "id": "lead_qa_sqlite",
            "workspace_id": "workspace_001",
            "company": "QA Co",
            "email": "qa@example.com",
        },
    )
    assert rec["id"] == "lead_qa_sqlite"
    assert get_by_id("leads", "lead_qa_sqlite")["company"] == "QA Co"
    updated = update_record("leads", "lead_qa_sqlite", {"notes": "hello"})
    assert updated["notes"] == "hello"
    assert delete_record("leads", "lead_qa_sqlite")
    assert get_by_id("leads", "lead_qa_sqlite") is None


def test_sqlite_relationships(tmp_path):
    _fresh_db(tmp_path)
    call = get_by_id("calls", sql_all("calls")[0]["id"])
    assert call["lead_id"]
    assert get_by_id("leads", call["lead_id"])
    for tr in sql_all("transcripts"):
        assert get_by_id("calls", tr["call_id"])


def test_sqlite_json_fallback(tmp_path):
    reset_datastore_state()
    from app import store

    store._sqlite_ready = False
    users = store.get_all("users")
    assert any(u.get("email") == "demo@example.com" for u in users)
    close_conn()


def test_sqlite_persists_after_reopen(tmp_path):
    path = _fresh_db(tmp_path)
    create_record(
        "leads",
        {
            "id": "lead_persist_qa",
            "workspace_id": "workspace_001",
            "company": "Persist Co",
            "notes": "must survive reopen",
        },
    )
    close_conn()
    reset_datastore_state()
    assert init_db(path, seed=True)
    from app import store

    store._sqlite_ready = True
    rec = get_by_id("leads", "lead_persist_qa")
    assert rec and rec["notes"] == "must survive reopen"
    assert get_by_id("users", "user_001")["email"] == "demo@example.com"
    assert count("users") == 2
