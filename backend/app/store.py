from __future__ import annotations

import json
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

DATA_DIR = Path(__file__).resolve().parent.parent / "mock_data"
_lock = threading.RLock()


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _path(collection: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"{collection}.json"


def read_json(collection: str) -> Any:
    p = _path(collection)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(collection: str, data: Any) -> None:
    p = _path(collection)
    tmp = p.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(p)


def get_all(collection: str) -> list[dict]:
    with _lock:
        data = read_json(collection)
        if not isinstance(data, list):
            return []
        return deepcopy(data)


def get_by_id(collection: str, record_id: str) -> dict | None:
    for row in get_all(collection):
        if row.get("id") == record_id:
            return row
    return None


def create_record(collection: str, record: dict) -> dict:
    with _lock:
        data = read_json(collection)
        if not isinstance(data, list):
            data = []
        if "id" not in record:
            record["id"] = new_id(collection[:4])
        data.append(record)
        write_json(collection, data)
        return deepcopy(record)


def update_record(collection: str, record_id: str, patch: dict) -> dict | None:
    with _lock:
        data = read_json(collection)
        for i, row in enumerate(data):
            if row.get("id") == record_id:
                row.update(patch)
                data[i] = row
                write_json(collection, data)
                return deepcopy(row)
        return None


def delete_record(collection: str, record_id: str) -> bool:
    with _lock:
        data = read_json(collection)
        next_data = [r for r in data if r.get("id") != record_id]
        if len(next_data) == len(data):
            return False
        write_json(collection, next_data)
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
    return filter_records(collection, lambda r: r.get("workspace_id") == workspace_id)


def audit(workspace_id: str | None, actor_user_id: str | None, action: str, entity: str, entity_id: str | None = None, meta: dict | None = None) -> None:
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
