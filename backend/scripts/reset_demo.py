"""Delete the local SQLite file and reseed from JSON demo data."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings  # noqa: E402
from app.db import close_conn, db_path, init_db  # noqa: E402
from app.seed import seed_from_json  # noqa: E402
from app.store import reset_datastore_state  # noqa: E402


def reset() -> None:
    reset_datastore_state()
    path = db_path()
    for suffix in ("", "-wal", "-shm", "-journal"):
        p = Path(str(path) + suffix) if suffix else path
        if p.exists():
            p.unlink()
    init_db(path, seed=True)
    seed_from_json(force=True)
    print("Demo SQLite reseeded at", path)


if __name__ == "__main__":
    reset()
