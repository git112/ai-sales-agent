from __future__ import annotations

import re
from pathlib import Path

PROTECTED_FIELDS = {
    "id",
    "workspace_id",
    "password_hash",
    "role",
    "owner_user_id",
    "openai_api_key",
    "jwt_secret",
}


def client_patch(payload: dict | None, extra_deny: set[str] | None = None) -> dict:
    deny = PROTECTED_FIELDS | (extra_deny or set())
    if not isinstance(payload, dict):
        return {}
    return {k: v for k, v in payload.items() if k not in deny}


def safe_filename(name: str | None, fallback: str = "upload.bin") -> str:
    base = Path(name or fallback).name
    base = base.replace("\x00", "")
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._") or fallback
    if base in {".", ".."}:
        return fallback
    return base[:120]


def safe_dest(root: Path, workspace_id: str, filename: str) -> Path:
    ws = re.sub(r"[^A-Za-z0-9._-]+", "_", workspace_id or "ws")[:64]
    dest_dir = (root / ws).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = (dest_dir / safe_filename(filename)).resolve()
    if dest_dir not in dest.parents and dest != dest_dir:
        raise ValueError("Invalid upload path")
    return dest
