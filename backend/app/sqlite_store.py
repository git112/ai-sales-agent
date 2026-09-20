from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from app.db import LIST_COLLECTIONS, _lock, get_conn

_INDEX_FIELDS = ("workspace_id", "email", "status", "lead_id", "campaign_id", "opportunity_id", "call_id", "created_at")


def _index_values(record: dict) -> dict:
    status = record.get("status")
    if status is None:
        status = record.get("pipeline_stage")
    created = record.get("created_at") or record.get("started_at") or record.get("last_updated")
    return {
        "id": record.get("id"),
        "workspace_id": record.get("workspace_id"),
        "email": record.get("email"),
        "status": status,
        "lead_id": record.get("lead_id"),
        "campaign_id": record.get("campaign_id"),
        "opportunity_id": record.get("opportunity_id"),
        "call_id": record.get("call_id"),
        "created_at": created,
        "payload": json.dumps(record, ensure_ascii=False),
    }


def _load(row) -> dict:
    return json.loads(row["payload"])


def _table(collection: str) -> str:
    if collection not in LIST_COLLECTIONS:
        raise KeyError(collection)
    return collection


def get_all(collection: str) -> list[dict]:
    if collection == "analytics":
        data = read_analytics()
        return data if isinstance(data, list) else []
    with _lock:
        rows = get_conn().execute(f"SELECT payload FROM {_table(collection)}").fetchall()
        return [_load(r) for r in rows]


def get_by_id(collection: str, record_id: str) -> dict | None:
    with _lock:
        row = get_conn().execute(f"SELECT payload FROM {_table(collection)} WHERE id = ?", (record_id,)).fetchone()
        return _load(row) if row else None


def by_workspace(collection: str, workspace_id: str) -> list[dict]:
    with _lock:
        rows = get_conn().execute(
            f"SELECT payload FROM {_table(collection)} WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchall()
        return [_load(r) for r in rows]


def create_record(collection: str, record: dict, ignore_duplicate: bool = False) -> dict:
    vals = _index_values(record)
    sql = (
        f"INSERT OR IGNORE INTO {_table(collection)} (id, workspace_id, email, status, lead_id, campaign_id, opportunity_id, call_id, created_at, payload) "
        "VALUES (:id, :workspace_id, :email, :status, :lead_id, :campaign_id, :opportunity_id, :call_id, :created_at, :payload)"
        if ignore_duplicate
        else (
            f"INSERT INTO {_table(collection)} (id, workspace_id, email, status, lead_id, campaign_id, opportunity_id, call_id, created_at, payload) "
            "VALUES (:id, :workspace_id, :email, :status, :lead_id, :campaign_id, :opportunity_id, :call_id, :created_at, :payload)"
        )
    )
    with _lock:
        conn = get_conn()
        conn.execute(sql, vals)
        conn.commit()
        stored = get_by_id(collection, record["id"])
        return deepcopy(stored or record)


def update_record(collection: str, record_id: str, patch: dict) -> dict | None:
    with _lock:
        current = get_by_id(collection, record_id)
        if not current:
            return None
        current.update(patch)
        vals = _index_values(current)
        conn = get_conn()
        conn.execute(
            f"""UPDATE {_table(collection)} SET
                workspace_id=:workspace_id, email=:email, status=:status, lead_id=:lead_id,
                campaign_id=:campaign_id, opportunity_id=:opportunity_id, call_id=:call_id,
                created_at=:created_at, payload=:payload
              WHERE id=:id""",
            vals,
        )
        conn.commit()
        return deepcopy(current)


def delete_record(collection: str, record_id: str) -> bool:
    with _lock:
        conn = get_conn()
        cur = conn.execute(f"DELETE FROM {_table(collection)} WHERE id = ?", (record_id,))
        conn.commit()
        return cur.rowcount > 0


def replace_collection(collection: str, rows: list[dict]) -> None:
    with _lock:
        conn = get_conn()
        conn.execute(f"DELETE FROM {_table(collection)}")
        for record in rows:
            if "id" not in record:
                continue
            conn.execute(
                f"INSERT INTO {_table(collection)} (id, workspace_id, email, status, lead_id, campaign_id, opportunity_id, call_id, created_at, payload) "
                "VALUES (:id, :workspace_id, :email, :status, :lead_id, :campaign_id, :opportunity_id, :call_id, :created_at, :payload)",
                _index_values(record),
            )
        conn.commit()


def read_analytics() -> dict:
    with _lock:
        rows = get_conn().execute("SELECT workspace_id, payload FROM analytics").fetchall()
        out = {}
        for row in rows:
            out[row["workspace_id"]] = json.loads(row["payload"])
        return out


def write_analytics(data: dict) -> None:
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM analytics")
        for wid, blob in (data or {}).items():
            conn.execute(
                "INSERT INTO analytics(workspace_id, payload) VALUES (?, ?)",
                (wid, json.dumps(blob, ensure_ascii=False)),
            )
        conn.commit()


def count(collection: str) -> int:
    with _lock:
        row = get_conn().execute(f"SELECT COUNT(*) AS n FROM {_table(collection)}").fetchone()
        return int(row["n"])
