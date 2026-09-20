from __future__ import annotations

import json
import os
import threading
import time
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

DATA_DIR = Path(__file__).resolve().parent.parent / "mock_data"
_lock = threading.RLock()
_sqlite_ready: bool | None = None


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _path(collection: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"{collection}.json"


def _json_read(collection: str) -> Any:
    p = _path(collection)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def _json_write(collection: str, data: Any) -> None:
    p = _path(collection)
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    tmp = p.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        f.write(payload)
    for _ in range(8):
        try:
            os.replace(tmp, p)
            return
        except PermissionError:
            time.sleep(0.05)
    with p.open("w", encoding="utf-8") as f:
        f.write(payload)
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass


def init_datastore() -> bool:
    global _sqlite_ready
    if _sqlite_ready is True:
        return True
    if _sqlite_ready is False:
        return False
    try:
        from app.db import init_db

        _sqlite_ready = bool(init_db())
    except Exception:
        print("SQLite unavailable — using JSON demo fallback", flush=True)
        _sqlite_ready = False
    return bool(_sqlite_ready)


def sqlite_active() -> bool:
    init_datastore()
    return bool(_sqlite_ready)


def reset_datastore_state() -> None:
    global _sqlite_ready
    _sqlite_ready = None
    try:
        from app.db import close_conn

        close_conn()
        from app import db as dbmod

        dbmod._failed = False
    except Exception:
        pass


def _sql():
    from app import sqlite_store

    return sqlite_store


def read_json(collection: str) -> Any:
    if collection == "analytics" and sqlite_active():
        return _sql().read_analytics()
    if sqlite_active() and collection != "public_feed":
        try:
            return _sql().get_all(collection)
        except KeyError:
            return _json_read(collection)
    return _json_read(collection)


def write_json(collection: str, data: Any) -> None:
    if collection == "analytics" and sqlite_active() and isinstance(data, dict):
        _sql().write_analytics(data)
        return
    if sqlite_active() and isinstance(data, list):
        try:
            _sql().replace_collection(collection, data)
            return
        except KeyError:
            pass
    _json_write(collection, data)


def get_all(collection: str) -> list[dict]:
    if sqlite_active():
        try:
            return _sql().get_all(collection)
        except KeyError:
            pass
    with _lock:
        data = _json_read(collection)
        if not isinstance(data, list):
            return []
        return deepcopy(data)


def get_by_id(collection: str, record_id: str) -> dict | None:
    if sqlite_active():
        try:
            return _sql().get_by_id(collection, record_id)
        except KeyError:
            pass
    for row in get_all(collection):
        if row.get("id") == record_id:
            return row
    return None


def create_record(collection: str, record: dict) -> dict:
    if "id" not in record:
        record["id"] = new_id(collection[:4])
    if sqlite_active():
        try:
            return _sql().create_record(collection, record)
        except KeyError:
            pass
    with _lock:
        data = _json_read(collection)
        if not isinstance(data, list):
            data = []
        data.append(record)
        _json_write(collection, data)
        return deepcopy(record)


def update_record(collection: str, record_id: str, patch: dict) -> dict | None:
    if sqlite_active():
        try:
            return _sql().update_record(collection, record_id, patch)
        except KeyError:
            pass
    with _lock:
        data = _json_read(collection)
        for i, row in enumerate(data):
            if row.get("id") == record_id:
                row.update(patch)
                data[i] = row
                _json_write(collection, data)
                return deepcopy(row)
        return None


def delete_record(collection: str, record_id: str) -> bool:
    if sqlite_active():
        try:
            return _sql().delete_record(collection, record_id)
        except KeyError:
            pass
    with _lock:
        data = _json_read(collection)
        next_data = [r for r in data if r.get("id") != record_id]
        if len(next_data) == len(data):
            return False
        _json_write(collection, next_data)
        return True


def filter_records(collection: str, predicate: Callable[[dict], bool]) -> list[dict]:
    return [r for r in get_all(collection) if predicate(r)]


def search_records(collection: str, query: str, fields: list[str]) -> list[dict]:
    q = (query or "").lower().strip()
    if not q:
        return get_all(collection)
    out = []
    for row in get_all(collection):
        blob = " ".join(str(row.get(f) or "") for f in fields).lower()
        if q in blob:
            out.append(row)
    return out


def by_workspace(collection: str, workspace_id: str) -> list[dict]:
    if sqlite_active():
        try:
            return _sql().by_workspace(collection, workspace_id)
        except KeyError:
            pass
    return filter_records(collection, lambda r: r.get("workspace_id") == workspace_id)


def audit(workspace_id: str | None, actor_user_id: str | None, action: str, entity: str, entity_id: str | None = None, meta: dict | None = None) -> None:
    try:
        create_record(
            "audit_logs",
            {
                "id": new_id("audit"),
                "workspace_id": workspace_id,
                "actor_user_id": actor_user_id,
                "action": action,
                "entity": entity,
                "entity_id": entity_id,
                "meta": meta or {},
                "created_at": utcnow(),
            },
        )
    except OSError:
        pass
