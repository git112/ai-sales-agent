"""Bolna live calling integration tests.

Run with: ./venv/bin/pytest tests/test_bolna_live.py -v

Tests exercise:
- Bolna payload construction for each language
- Active-language resolution from lead location
- Outcome mapping for Bolna status codes
- Transcript extraction from execution payload
- The Bolna webhook -> call record reconcile path (with Bolna API mocked)
"""
from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-test")

from app import bolna as bolna_mod
from app.bolna import (
    TERMINAL_STATUSES,
    _active_language,
    build_agent_payload,
    extract_outcome,
    extract_transcript_turns,
)
from app.live_voice import LiveVoiceProvider


@pytest.fixture
def sample_agent():
    return {
        "id": "agent_001",
        "name": "Lumina Test Agent",
        "company_name": "Northwind Digital",
        "call_objective": "qualify SharePoint migration interest",
        "guardrails": ["disclose AI"],
    }


def test_build_agent_payload_has_six_languages(sample_agent):
    p = build_agent_payload(sample_agent)
    langs = p["agent_config"]["tasks"][0]["tools_config"]["multilingual_config"]["languages"]
    assert set(langs.keys()) == {"en", "hi", "gu", "es", "fr", "de"}
    for code, entry in langs.items():
        assert entry["system_prompt"]
        assert entry["synthesizer"]["provider_config"]["language"] == code
        assert entry["transcriber"]["language"]


def test_build_agent_payload_default_language_english(sample_agent):
    p = build_agent_payload(sample_agent)
    assert p["agent_config"]["tasks"][0]["tools_config"]["multilingual_config"]["active_language"] == "en"
    # task_1.system_prompt should be a non-empty English prompt
    assert "Northwind Digital" in p["agent_prompts"]["task_1"]["system_prompt"]


def test_active_language_resolution():
    assert _active_language("en", None) == "en"
    assert _active_language("hi", None) == "hi"
    assert _active_language("gu", None) == "gu"
    assert _active_language("auto", {"location": "Ahmedabad, Gujarat"}) == "gu"
    assert _active_language("auto", {"location": "Mumbai, India"}) == "hi"
    assert _active_language("auto", {"location": "Madrid, Spain"}) == "es"
    assert _active_language("auto", {"location": "Berlin, Germany"}) == "de"
    assert _active_language("auto", {"location": "Unknown"}) == "en"


def test_outcome_mapping():
    assert extract_outcome({"status": "completed"}) == "Connected"
    assert extract_outcome({"status": "no-answer"}) == "No Answer"
    assert extract_outcome({"status": "busy"}) == "No Answer"
    assert extract_outcome({"status": "failed"}) == "Failed"
    assert extract_outcome({"status": "in-progress"}) == "Connected"
    assert extract_outcome({"status": "balance-low"}) == "Failed"
    assert extract_outcome({"status": "in-progress", "answered_by_voice_mail": True}) == "Voicemail"


def test_terminal_statuses_includes_real_codes():
    assert "completed" in TERMINAL_STATUSES
    assert "no-answer" in TERMINAL_STATUSES
    assert "failed" in TERMINAL_STATUSES
    assert "in-progress" not in TERMINAL_STATUSES


def test_extract_transcript_turns_dict_list():
    turns = extract_transcript_turns({
        "transcript": [
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "Hi"},
        ]
    })
    assert turns == [
        {"speaker": "agent", "text": "Hello"},
        {"speaker": "prospect", "text": "Hi"},
    ]


def test_extract_transcript_turns_string_fallback():
    turns = extract_transcript_turns({"transcript": "Single string transcript"})
    assert len(turns) == 1
    assert turns[0]["speaker"] == "agent"


def test_live_voice_sync_creates_agent_when_not_synced(sample_agent, monkeypatch):
    monkeypatch.setattr(bolna_mod, "is_configured", lambda: True)
    fake_create = MagicMock(return_value="bolna-uuid-123")
    monkeypatch.setattr(bolna_mod, "create_agent", fake_create)
    lv = LiveVoiceProvider()
    out = lv.sync_agent(sample_agent)
    assert out == "bolna-uuid-123"
    fake_create.assert_called_once()


def test_live_voice_sync_patches_when_already_synced(sample_agent, monkeypatch):
    sample_agent["bolna_agent_id"] = "existing-id"
    monkeypatch.setattr(bolna_mod, "is_configured", lambda: True)
    fake_patch = MagicMock(return_value={"status": "ok"})
    monkeypatch.setattr(bolna_mod, "patch_agent", fake_patch)
    fake_create = MagicMock()
    monkeypatch.setattr(bolna_mod, "create_agent", fake_create)
    lv = LiveVoiceProvider()
    out = lv.sync_agent(sample_agent)
    assert out == "existing-id"
    fake_patch.assert_called_once()
    fake_create.assert_not_called()


def test_live_voice_dispatch_passes_user_data(sample_agent, monkeypatch):
    monkeypatch.setattr(bolna_mod, "is_configured", lambda: True)
    captured = {}

    def fake_dispatch_call(**kw):
        captured.update(kw)
        return {"execution_id": "exec-1", "status": "queued"}

    monkeypatch.setattr(bolna_mod, "dispatch_call", fake_dispatch_call)
    lv = LiveVoiceProvider()
    sample_agent["bolna_agent_id"] = "agent-x"
    resp = lv.dispatch(
        agent=sample_agent,
        recipient_phone="+15551234567",
        lead={"id": "lead1", "name": "Acme Co", "location": "Ahmedabad"},
        from_phone="+15550000000",
        language="auto",
    )
    assert resp["execution_id"] == "exec-1"
    assert captured["recipient"] == "+15551234567"
    assert captured["from_phone"] == "+15550000000"
    assert captured["user_data"]["prospect_name"] == "Acme Co"
    assert captured["user_data"]["language"] == "gu"


def test_webhook_reconcile_upserts_call_record(monkeypatch):
    from fastapi.testclient import TestClient

    # Reset datastore
    from app.store import init_datastore
    init_datastore()

    # Patch the bolna client dispatch to bypass real API
    monkeypatch.setattr(bolna_mod, "is_configured", lambda: True)
    monkeypatch.setattr(bolna_mod, "dispatch_call", lambda **kw: {"execution_id": "exec-xyz", "status": "queued"})

    # Avoid pulling in chatty tests, just hit /bolna/webhook with a fake execution
    from app.main import app
    client = TestClient(app)

    # Inject a fake call into the in-memory store (unique execution id per run)
    import uuid

    from app.store import create_record, new_id
    wid = "ws-test"
    exec_id = f"exec-test-{uuid.uuid4().hex[:8]}"
    cid = new_id("call")
    create_record("calls", {
        "id": cid,
        "workspace_id": wid,
        "lead_id": "lead-x",
        "agent_id": "agent-y",
        "bolna_execution_id": exec_id,
        "mode": "live",
        "outcome": "Queued",
        "is_demo": False,
    })

    payload = {
        "execution_id": exec_id,
        "status": "completed",
        "conversation_time": 42,
        "recording_url": "https://example.com/r.mp3",
        "transcript": [
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "I'm interested"},
        ],
        "extracted_data": {
            "interest_level": "interested",
            "high_intent": True,
            "requirements": "SharePoint migration",
            "timeline": "Q1",
        },
    }
    r = client.post("/api/v1/bolna/webhook", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["processed"] is True
    assert body["details"]["outcome"] == "Connected"
    assert body["details"]["call_id"] == cid
