from __future__ import annotations

import json

import pytest
from app.calendly_service import (
    complete_calendly_booking,
    check_unbooked_and_recall,
    get_preferred_timeslots,
    schedule_callback,
    send_calendly_sms,
)
from app.store import create_record, get_by_id, new_id, utcnow
from app.voice import agent_reply, parse_callback_request, scripts


def test_voice_handoff_mentions_calendly_sms():
    agent = {"id": "agent_test", "name": "Alex"}
    res = agent_reply(agent, "I want to speak with a human please", [], "en")
    assert res["escalated"] is True
    assert res["outcome"] == "Escalated"
    assert "Calendly" in res["reply"] or "texted you" in res["reply"]


def test_voice_calendly_recall():
    agent = {"id": "agent_test", "name": "Alex"}
    res = agent_reply(agent, "Hi, I haven't booked a timeslot yet.", [], "en")
    assert res["outcome"] == "Connected"
    assert "Calendly" in res["reply"] or "timeslot" in res["reply"]


def test_send_calendly_sms_and_booking_flow():
    wid = "workspace_001"
    lead_id = new_id("lead")
    create_record(
        "leads",
        {
            "id": lead_id,
            "workspace_id": wid,
            "company": "Contoso Enterprise",
            "name": "Jane Doe",
            "phone": "+1 (555) 321-4321",
            "pipeline_stage": "contacted",
            "qualification_status": "in_progress",
        },
    )

    # 1. Send Calendly SMS during human handoff
    sms_res = send_calendly_sms(wid, lead_id, to_phone="+1 (555) 321-4321")
    assert sms_res["booking"]["status"] == "pending_booking"
    assert "calendly.com" in sms_res["calendly_link"]
    assert sms_res["sms"]["status"] in ("delivered", "sent")
    assert sms_res["sms"]["to_phone"] == "+1 (555) 321-4321"

    booking_id = sms_res["booking"]["id"]

    # 2. Book via Calendly
    book_res = complete_calendly_booking(
        wid,
        booking_id=booking_id,
        lead_id=lead_id,
        slot_id="slot_today_2pm",
        slot_title="Today · 2:00 PM – 2:30 PM (EST)",
        specialist="Sarah Jenkins",
        notes="Excited for discovery session",
    )
    assert book_res["ok"] is True
    assert book_res["booking"]["status"] == "booked"
    assert book_res["details"]["timeslot"] == "Today · 2:00 PM – 2:30 PM (EST)"

    updated_lead = get_by_id("leads", lead_id)
    assert updated_lead["pipeline_stage"] == "meeting_scheduled"
    assert updated_lead["calendly_booked"] is True


def test_unbooked_calendly_auto_recall():
    wid = "workspace_001"
    lead_id = new_id("lead")
    create_record(
        "leads",
        {
            "id": lead_id,
            "workspace_id": wid,
            "company": "Fabrikam Aerospace",
            "name": "Robert Taylor",
            "phone": "+1 (555) 888-9999",
            "pipeline_stage": "contacted",
            "qualification_status": "in_progress",
        },
    )

    # Dispatch Calendly SMS
    sms_res = send_calendly_sms(wid, lead_id, to_phone="+1 (555) 888-9999")
    booking_id = sms_res["booking"]["id"]
    assert sms_res["booking"]["status"] == "pending_booking"

    # Simulate lead NOT booking: system checks and triggers auto-recall!
    recalls = check_unbooked_and_recall(wid, lead_id=lead_id, force_immediate=True)
    assert len(recalls) >= 1
    recalled_item = next(r for r in recalls if r["lead_id"] == lead_id)
    assert recalled_item["status"] == "recalled"

    # Verify the booking status transitioned to recalled
    booking = get_by_id("calendly_bookings", booking_id)
    assert booking["status"] == "recalled"
    assert booking["recall_call_id"] is not None

    # Verify the recall call record
    recall_call = get_by_id("calls", booking["recall_call_id"])
    assert recall_call["is_recall"] is True
    assert recall_call["recall_reason"] == "unbooked_calendly_link"


def test_api_endpoints():
    from starlette.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    # 1. Preferred slots
    r = client.get("/api/v1/calendly/preferred-slots")
    assert r.status_code == 200
    slots = r.json()
    assert len(slots) >= 3
    assert any("2:00 PM" in s["title"] for s in slots)

    # 2. SMS logs — requires auth token; without one, 401 is correct
    r = client.get("/api/v1/sms-logs", headers={"X-Workspace-Id": "workspace_001"})
    assert r.status_code == 401  # expected: protected endpoint, no token supplied


def _sign(secret: str, ts: str, body: bytes) -> str:
    import hmac as _hmac, hashlib as _hl
    return _hmac.new(secret.encode(), ts.encode("ascii") + b"." + body, _hl.sha256).hexdigest()


def test_calendly_webhook_signature_verification(monkeypatch):
    """Verify Calendly webhook signatures per https://developer.calendly.com/api-docs/.
    Header: 't=<unix_ts>,v1=<hex_hmac_sha256>'. Signed payload: '<t>.<raw_body>'."""
    import os as _os
    import time as _time
    from starlette.testclient import TestClient
    from app.main import app

    secret = "test_signing_key_xyz"
    monkeypatch.setenv("CALENDLY_WEBHOOK_SECRET", secret)

    client = TestClient(app)
    body = b'{"event":"invitee.created","payload":{"tracking":{"utm_source":"lead_x","utm_content":"cal_bk_y"}}}'
    ts = str(int(_time.time()))

    # 1. Valid signature → reaches event handler
    v1 = _sign(secret, ts, body)
    r = client.post(
        "/api/v1/calendly/webhook",
        content=body,
        headers={
            "Calendly-Webhook-Signature": f"t={ts},v1={v1}",
            "Content-Type": "application/json",
            "X-Workspace-Id": "workspace_001",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json().get("event") == "invitee.created"

    # 2. Tampered body → 403
    r = client.post(
        "/api/v1/calendly/webhook",
        content=body + b"x",
        headers={
            "Calendly-Webhook-Signature": f"t={ts},v1={v1}",
            "Content-Type": "application/json",
            "X-Workspace-Id": "workspace_001",
        },
    )
    assert r.status_code == 403

    # 3. Wrong key → 403
    r = client.post(
        "/api/v1/calendly/webhook",
        content=body,
        headers={
            "Calendly-Webhook-Signature": f"t={ts},v1={_sign('wrong', ts, body)}",
            "Content-Type": "application/json",
            "X-Workspace-Id": "workspace_001",
        },
    )
    assert r.status_code == 403

    # 4. Stale timestamp (> 3 min) → 403 (replay protection)
    stale_ts = str(int(_time.time()) - 600)
    r = client.post(
        "/api/v1/calendly/webhook",
        content=body,
        headers={
            "Calendly-Webhook-Signature": f"t={stale_ts},v1={_sign(secret, stale_ts, body)}",
            "Content-Type": "application/json",
            "X-Workspace-Id": "workspace_001",
        },
    )
    assert r.status_code == 403

    # 5. Malformed header → 403
    r = client.post(
        "/api/v1/calendly/webhook",
        content=body,
        headers={"Calendly-Webhook-Signature": "garbage", "X-Workspace-Id": "workspace_001"},
    )
    assert r.status_code == 403


def test_calendly_webhook_signature_disabled_when_secret_unset(monkeypatch):
    """No CALENDLY_WEBHOOK_SECRET → verification skipped (demo mode)."""
    monkeypatch.delenv("CALENDLY_WEBHOOK_SECRET", raising=False)
    from starlette.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    body = b'{"event":"routing_form_submission","payload":{}}'
    r = client.post(
        "/api/v1/calendly/webhook",
        content=body,
        headers={"X-Workspace-Id": "workspace_001"},
    )
    assert r.status_code == 200
    assert r.json().get("action") == "ignored"


# ──────────────────────────────────────────────────────────────────────────────
# parse_callback_request — time/date extraction from prospect speech
# ──────────────────────────────────────────────────────────────────────────────

from datetime import datetime, timezone, timedelta

@pytest.mark.parametrize("utterance,expected_label_part", [
    ("call me tomorrow at 11 am",                "11:00 AM"),
    ("we are looking for sharepoint migration support and want to start this month. you are hitting for me tomorrow morning at eleven am", "11:00 AM"),
    ("tomorrow morning at 11",                    "11:00 AM"),
    ("today at 4:30 pm",                          "4:30 PM"),
    ("call me back at 2pm",                       "2:00 PM"),
    ("hitting for me tomorrow at 11 am",          "11:00 AM"),
    ("tomorrow at 5 in the evening",              "5:00 PM"),
])
def test_parse_callback_request_recognises_time(utterance, expected_label_part):
    parsed = parse_callback_request(utterance)
    assert parsed is not None, f"failed to parse: {utterance!r}"
    assert expected_label_part in parsed["label"]


def test_parse_callback_request_returns_none_when_no_time():
    assert parse_callback_request("we are looking for sharepoint support") is None
    assert parse_callback_request("") is None
    assert parse_callback_request("transfer me to a real person") is None


def test_schedule_callback_creates_pending_booking_and_sends_sms():
    wid = "workspace_001"
    lead_id = new_id("lead")
    create_record(
        "leads",
        {
            "id": lead_id,
            "workspace_id": wid,
            "company": "Northwind Beta",
            "name": "Anita Verma",
            "phone": "+1 (555) 444-2211",
            "pipeline_stage": "contacted",
            "qualification_status": "in_progress",
        },
    )
    parsed = parse_callback_request("call me tomorrow at 11 am")
    assert parsed is not None
    res = schedule_callback(
        workspace_id=wid,
        lead_id=lead_id,
        parsed=parsed,
        call_id=None,
        campaign_id=None,
        raw_user_text="call me tomorrow at 11 am",
    )
    assert res["booking"]["status"] == "pending_booking"
    assert res["booking"]["requested_slot"]["time"] == "11:00"
    assert "calendly.com" in res["calendly_link"]
    assert res["sms"]["to_phone"] == "+1 (555) 444-2211"
    # With DEFAULT_LEAD_EMAIL set, the confirmation email goes to the placeholder address
    assert res["email"] == "23it021@charusat.edu.in"
    assert res["lead_email_original"] == ""
    # lead promoted to callback_scheduled, NOT marked lost
    lead = get_by_id("leads", lead_id)
    assert lead["pipeline_stage"] == "callback_scheduled"
    assert lead["intent_level"] == "Interested"
    assert lead["calendly_slot"] == parsed["label"]


def test_bolna_speaker_extraction_strips_prefix():
    from app.bolna import extract_transcript_turns
    payload = {
        "transcript": [
            {"role": "assistant", "content": "assistant: Hello there."},
            {"role": "user",      "content": "user:  i want to talk"},
            {"role": "assistant", "content": "assistant: Sure, when works?"},
            {"role": "user",      "content": "user: tomorrow at 11 am"},
        ]
    }
    turns = extract_transcript_turns(payload)
    assert [t["speaker"] for t in turns] == ["agent", "prospect", "agent", "prospect"]
    assert turns[0]["text"] == "Hello there."
    assert turns[1]["text"] == "i want to talk"
    assert turns[3]["text"] == "tomorrow at 11 am"


def test_bolna_speaker_extraction_handles_missing_role():
    from app.bolna import extract_transcript_turns
    turns = extract_transcript_turns({"transcript": [{"content": "user: hello"}]})
    assert turns[0]["speaker"] == "prospect"
    assert turns[0]["text"] == "hello"


# ──────────────────────────────────────────────────────────────────────────────
# Calendly API integration — fires built-in confirmation email
# ──────────────────────────────────────────────────────────────────────────────

class _FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body)

    def json(self):
        return self._body


def test_schedule_callback_uses_calendly_api_when_configured(monkeypatch):
    """With token + event_type + email, schedule_callback must hit
    POST /scheduled_events so Calendly fires the built-in confirmation email."""
    # Clear any cached event_type URI from prior runs so the test isn't poisoned.
    from app.db import init_db, meta_set
    try:
        meta_set("calendly_event_type_uri", "")
    except Exception:
        pass

    wid = "workspace_001"
    lead_id = new_id("lead")
    create_record(
        "leads",
        {
            "id": lead_id,
            "workspace_id": wid,
            "company": "Calendly Test Co",
            "name": "Cara Lin",
            "email": "cara@calendly-test.example",
            "phone": "+1 (555) 999-0000",
            "pipeline_stage": "contacted",
            "qualification_status": "in_progress",
        },
    )

    monkeypatch.setenv("CALENDLY_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("CALENDLY_EVENT_TYPE_URI", "https://api.calendly.com/event_types/E1")

    import httpx as _httpx
    calls = {"scheduled_events": 0, "users_me": 0, "event_types": 0}

    import json as _json
    def fake_post(*args, **kwargs):
        calls["scheduled_events"] += 1
        payload = kwargs.get("json") or (args[1] if len(args) > 1 else None)
        # With DEFAULT_LEAD_EMAIL set, Calendly API gets the placeholder email
        assert payload and payload.get("invitee", {}).get("email") == "23it021@charusat.edu.in"
        print(f"FAKE_POST CALLED returns 201", flush=True)
        return _FakeResponse(201, {
            "resource": {
                "uri": "https://api.calendly.com/scheduled_events/SE1",
                "invitee_counter": {"uri": "https://api.calendly.com/scheduled_events/SE1/invitees/I1"},
            }
        })

    def fake_get(*args, **kwargs):
        url = args[0] if args else kwargs.get("url", "")
        if "users/me" in url:
            calls["users_me"] += 1
            return _FakeResponse(200, {"resource": {"uri": "https://api.calendly.com/users/U1"}})
        if "event_types" in url:
            calls["event_types"] += 1
            return _FakeResponse(200, {"collection": [{"uri": "https://api.calendly.com/event_types/E_DISCOVERED"}]})
        return _FakeResponse(404, {"error": "not_found"})

    monkeypatch.setattr(_httpx, "post", fake_post)
    monkeypatch.setattr(_httpx, "get", fake_get)

    parsed = parse_callback_request("call me tomorrow at 11 am")
    res = schedule_callback(
        workspace_id=wid, lead_id=lead_id, parsed=parsed, raw_user_text="call me tomorrow at 11 am"
    )

    assert calls["scheduled_events"] == 1, "expected Calendly API call to fire confirmation email"
    assert res["delivery_channel"] == "calendly_email", (
        f"expected calendly_email, got {res['delivery_channel']!r}; "
        f"calendly_api={res.get('calendly_event_uri')}"
    )
    assert res["calendly_event_uri"] == "https://api.calendly.com/scheduled_events/SE1"
    assert res["booking"]["status"] == "booked"
    assert res["booking"]["delivery_channel"] == "calendly_email"

    lead = get_by_id("leads", lead_id)
    assert lead["pipeline_stage"] == "meeting_scheduled"
    assert lead["calendly_booked"] is True


def test_schedule_callback_falls_back_to_sms_when_no_token(monkeypatch):
    """No Calendly token → fall back to Twilio SMS for the link."""
    monkeypatch.delenv("CALENDLY_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("CALENDLY_EVENT_TYPE_URI", raising=False)

    wid = "workspace_001"
    lead_id = new_id("lead")
    create_record(
        "leads",
        {
            "id": lead_id,
            "workspace_id": wid,
            "company": "Fallback Co",
            "name": "Frank Fall",
            "email": "frank@fallback.example",
            "phone": "+1 (555) 111-2222",
            "pipeline_stage": "contacted",
            "qualification_status": "in_progress",
        },
    )

    import httpx as _httpx
    def fail(*a, **k): raise AssertionError("Calendly API should not be called without a token")
    monkeypatch.setattr(_httpx, "post", fail)
    monkeypatch.setattr(_httpx, "get", fail)

    parsed = parse_callback_request("call me tomorrow at 3 pm")
    res = schedule_callback(workspace_id=wid, lead_id=lead_id, parsed=parsed)
    assert res["delivery_channel"] == "simulated_sms"
    assert res["calendly_event_uri"] is None
    assert res["booking"]["status"] == "pending_booking"


def test_schedule_callback_no_phone_no_email_records_skipped(monkeypatch):
    """Lead without email + no Calendly token + no phone → records booking,
    skips both email and SMS, surfaces in notification."""
    monkeypatch.delenv("CALENDLY_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("CALENDLY_EVENT_TYPE_URI", raising=False)

    wid = "workspace_001"
    lead_id = new_id("lead")
    create_record(
        "leads",
        {
            "id": lead_id,
            "workspace_id": wid,
            "company": "NoContact Co",
            "name": "Nina Nobody",
            "phone": "",
            "email": "",
            "pipeline_stage": "contacted",
            "qualification_status": "in_progress",
        },
    )

    import httpx as _httpx
    monkeypatch.setattr(_httpx, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no api call expected")))
    monkeypatch.setattr(_httpx, "get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no api call expected")))

    parsed = parse_callback_request("tomorrow at 9 am")
    res = schedule_callback(workspace_id=wid, lead_id=lead_id, parsed=parsed)
    assert res["delivery_channel"] == "simulated_sms"
    assert res["sms"]["status"] == "no_phone_no_email"
    assert res["calendly_event_uri"] is None


def test_schedule_callback_falls_back_on_api_error(monkeypatch):
    """If Calendly API rejects the request (missing scope), gracefully fall back."""
    monkeypatch.setenv("CALENDLY_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("CALENDLY_EVENT_TYPE_URI", "https://api.calendly.com/event_types/E1")

    wid = "workspace_001"
    lead_id = new_id("lead")
    create_record(
        "leads",
        {
            "id": lead_id,
            "workspace_id": wid,
            "company": "ApiErr Co",
            "name": "Ada Err",
            "email": "ada@apierr.example",
            "phone": "+1 (555) 333-4444",
            "pipeline_stage": "contacted",
            "qualification_status": "in_progress",
        },
    )

    import httpx as _httpx
    def fake_post(url, **k):
        return _FakeResponse(403, {"error": "missing_scope", "details": [{"message": "scheduled_events:write required"}]})
    monkeypatch.setattr(_httpx, "post", fake_post)
    monkeypatch.setattr(_httpx, "get", lambda *a, **k: _FakeResponse(404, {}))

    parsed = parse_callback_request("tomorrow at 2 pm")
    res = schedule_callback(workspace_id=wid, lead_id=lead_id, parsed=parsed)
    assert res["delivery_channel"] == "simulated_sms"
    assert res["calendly_event_uri"] is None
    assert res["booking"]["status"] == "pending_booking"
    lead = get_by_id("leads", lead_id)
    assert lead["pipeline_stage"] == "callback_scheduled"


# ──────────────────────────────────────────────────────────────────────────────
# URL encoding — redirect_uri must be encoded so the query string stays valid
# ──────────────────────────────────────────────────────────────────────────────

def test_calendly_link_url_encodes_params():
    from app.calendly_service import _build_calendly_link
    url = _build_calendly_link("lead_abc", "cal_bk_xyz")
    assert "?" in url
    parsed = url.split("?", 1)[1]
    # No redirect_uri (localhost unreachable from Calendly) — just tracking params
    params = {p.split("=")[0] for p in parsed.split("&") if p}
    assert "lead_id" in params
    assert "booking_ref" in params
    assert "utm_source" in params
    assert "utm_content" in params
    assert "redirect_uri" not in params


def test_schedule_callback_link_contains_time_params(monkeypatch):
    monkeypatch.delenv("CALENDLY_ACCESS_TOKEN", raising=False)
    wid = "workspace_001"
    lead_id = new_id("lead")
    create_record("leads", {
        "id": lead_id, "workspace_id": wid, "company": "X", "name": "Y",
        "email": "y@x.example", "phone": "+1 (555) 000-0000",
        "pipeline_stage": "contacted",
    })
    parsed = parse_callback_request("tomorrow at 11 am")
    res = schedule_callback(workspace_id=wid, lead_id=lead_id, parsed=parsed)
    from urllib.parse import urlparse, parse_qs
    qs = parse_qs(urlparse(res["calendly_link"]).query)
    assert qs["a1"] == ["time_requested"]
    assert qs["a2"] == [parsed["date"]]
    assert qs["a3"] == [parsed["time"]]
    # No redirect_uri
    assert "redirect_uri" not in qs


def test_schedule_callback_endpoint_rejects_unparseable_time(monkeypatch):
    from starlette.testclient import TestClient
    from app.main import app
    wid = "workspace_001"
    lead_id = new_id("lead")
    create_record("leads", {"id": lead_id, "workspace_id": wid, "company": "X", "name": "Y", "phone": "+1", "email": "y@x.example"})
    with TestClient(app) as client:
        token = client.post("/api/v1/auth/login", json={"email": "demo@example.com", "password": "Demo123!"}).json()["token"]
        r = client.post(
            "/api/v1/calendly/schedule-callback",
            json={"lead_id": lead_id, "time_text": "no time here"},
            headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": wid},
        )
    assert r.status_code == 400


def test_schedule_callback_endpoint_creates_booking(monkeypatch):
    monkeypatch.delenv("CALENDLY_ACCESS_TOKEN", raising=False)
    from starlette.testclient import TestClient
    from app.main import app
    wid = "workspace_001"
    lead_id = new_id("lead")
    create_record("leads", {"id": lead_id, "workspace_id": wid, "company": "Endpoint Co", "name": "E", "phone": "+1", "email": "e@x.example"})
    with TestClient(app) as client:
        token = client.post("/api/v1/auth/login", json={"email": "demo@example.com", "password": "Demo123!"}).json()["token"]
        r = client.post(
            "/api/v1/calendly/schedule-callback",
            json={"lead_id": lead_id, "time_text": "tomorrow at 3 pm"},
            headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": wid},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["parsed"]["time"] == "15:00"
    # DEFAULT_LEAD_EMAIL overrides the lead's real email
    assert body["email"] == "23it021@charusat.edu.in"
