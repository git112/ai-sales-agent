from __future__ import annotations

import pytest
from app.calendly_service import (
    complete_calendly_booking,
    check_unbooked_and_recall,
    get_preferred_timeslots,
    send_calendly_sms,
)
from app.store import create_record, get_by_id, new_id, utcnow
from app.voice import agent_reply, scripts


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
