from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.ai import DemoAIProvider
from app.core.config import settings
from app.db import close_conn, get_conn, init_db
from app.sanitize import client_patch, safe_dest, safe_filename
from app.store import reset_datastore_state
from app.url_analysis import validate_url


def test_client_patch_strips_security_fields():
    out = client_patch(
        {
            "notes": "ok",
            "workspace_id": "workspace_hacker",
            "id": "lead_other",
            "role": "admin",
            "password_hash": "x",
        }
    )
    assert out == {"notes": "ok"}


def test_safe_filename_blocks_traversal():
    assert ".." not in safe_filename("../../etc/passwd")
    dest = safe_dest(Path("backend/uploads"), "workspace_001", "..\\..\\windows\\system32\\x.txt")
    assert dest.name.endswith(".txt") or dest.name
    assert "workspace_001" in str(dest)


def test_ipv6_loopback_and_ula_blocked():
    for blocked in ("http://[::1]/", "https://[fd00::1]/", "http://[fe80::1]/"):
        try:
            validate_url(blocked)
            assert False, blocked
        except ValueError:
            pass


def test_copilot_does_not_cite_other_workspace_abc(monkeypatch):
    provider = DemoAIProvider()

    def empty(*_a, **_k):
        return []

    monkeypatch.setattr("app.ai.by_workspace", empty)
    out = provider.copilot("Show high-intent leads.", "workspace_other")
    ids = [c.get("id") for c in out["citations"]]
    assert "lead_abc" not in ids
    assert "ABC Technologies" not in out["answer"]


def test_sqlite_integrity_and_fk(tmp_path: Path):
    reset_datastore_state()
    settings.sqlite_path = str(tmp_path / "sales_agent.db")
    assert init_db(tmp_path / "sales_agent.db", seed=True)
    conn = get_conn()
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    close_conn()


def test_tenant_cannot_override_workspace_header(tmp_path: Path):
    reset_datastore_state()
    settings.sqlite_path = str(tmp_path / "iso.db")
    close_conn()
    from app.main import app

    with TestClient(app) as client:
        login = client.post("/api/v1/auth/login", json={"email": "demo@example.com", "password": "Demo123!"})
        assert login.status_code == 200
        token = login.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "X-Workspace-Id": "workspace_does_not_exist"}
        r = client.get("/api/v1/opportunities/opp_abc", headers=headers)
        assert r.status_code == 404
        r2 = client.get("/api/v1/opportunities/opp_abc", headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200
        r3 = client.patch(
            "/api/v1/leads/lead_abc",
            headers={"Authorization": f"Bearer {token}"},
            json={"workspace_id": "workspace_stolen", "notes": "isolation-check"},
        )
        assert r3.status_code == 200
        body = r3.json()
        assert body.get("workspace_id") == "workspace_001"
        assert "isolation-check" in (body.get("notes") or "")
        r4 = client.get("/health")
        assert r4.json().get("datastore") == "sqlite"
