from __future__ import annotations

import json
import logging
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.store import (
    by_workspace,
    create_record,
    get_all,
    get_by_id,
    new_id,
    update_record,
    utcnow,
)
from app.voice import scripts


def _meta_get(key: str) -> str | None:
    from app.db import meta_get
    return meta_get(key)


def _meta_set(key: str, value: str) -> None:
    from app.db import meta_set
    meta_set(key, value)


log = logging.getLogger("lumina.calendly")

# NOTE: CALENDLY_URL is re-read on every link build (see _get_calendly_url())
# so .env changes take effect without restarting the server.
DEFAULT_CALENDLY_URL = os.getenv("CALENDLY_URL", "https://calendly.com/northwind-digital/consultation")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
CALENDLY_API = "https://api.calendly.com"

# When set, every scheduled-meeting email is sent to this address INSTEAD OF
# the lead's own email. Use during testing when leads don't have real addresses.
# Set to empty string in .env (DEFAULT_LEAD_EMAIL=) to fall back to per-lead email.
DEFAULT_LEAD_EMAIL = os.getenv("DEFAULT_LEAD_EMAIL", "23it021@charusat.edu.in")


def _resolve_send_email(lead_email: str | None) -> str:
    """
    Returns the address Calendly should send the confirmation email TO.
    If DEFAULT_LEAD_EMAIL is set, it overrides the lead's own email
    (useful for hackathon/demo mode when leads don't have real inboxes).
    Re-reads env on every call so tests / .env edits take effect live.
    """
    override = (os.getenv("DEFAULT_LEAD_EMAIL", DEFAULT_LEAD_EMAIL) or "").strip()
    if override:
        return override
    return (lead_email or "").strip()


def _get_calendly_url() -> str:
    val = os.getenv("CALENDLY_URL", "").strip()
    return val or DEFAULT_CALENDLY_URL


def _build_calendly_link(lead_id: str, booking_id: str, extra: dict | None = None) -> str:
    """
    Build a Calendly booking link the lead actually opens.
    The base URL (CALENDLY_URL) is the public scheduling page, e.g.
    https://calendly.com/nanditkalaria27/30min
    We append lead/booking tracking params so the webhook fires with matching metadata.
    Note: redirect_uri is intentionally omitted — Calendly can't reach localhost.
    The booking confirmation comes via webhook (if CALENDLY_WEBHOOK_SECRET is set).
    """
    params = {
        "lead_id": lead_id,
        "booking_ref": booking_id,
        "utm_source": lead_id,
        "utm_content": booking_id,
    }
    if extra:
        params.update({k: str(v) for k, v in extra.items() if v is not None})
    return f"{_get_calendly_url()}?{urllib.parse.urlencode(params)}"

PREFERRED_TIMESLOTS = [
    {
        "id": "slot_today_2pm",
        "title": "Today · 2:00 PM – 2:30 PM (EST)",
        "date_label": "Today",
        "time_label": "2:00 PM",
        "duration": "30 mins",
        "specialist": "Sarah Jenkins",
        "role": "Lead Solutions Architect",
        "status": "available",
    },
    {
        "id": "slot_today_430pm",
        "title": "Today · 4:30 PM – 5:00 PM (EST)",
        "date_label": "Today",
        "time_label": "4:30 PM",
        "duration": "30 mins",
        "specialist": "David Chen",
        "role": "Enterprise SharePoint Consultant",
        "status": "available",
    },
    {
        "id": "slot_tomorrow_10am",
        "title": "Tomorrow · 10:00 AM – 10:30 AM (EST)",
        "date_label": "Tomorrow",
        "time_label": "10:00 AM",
        "duration": "30 mins",
        "specialist": "Sarah Jenkins",
        "role": "Lead Solutions Architect",
        "status": "available",
    },
    {
        "id": "slot_tomorrow_2pm",
        "title": "Tomorrow · 2:00 PM – 2:30 PM (EST)",
        "date_label": "Tomorrow",
        "time_label": "2:00 PM",
        "duration": "30 mins",
        "specialist": "Elena Rostova",
        "role": "Customer Success & Delivery Lead",
        "status": "available",
    },
    {
        "id": "slot_mon_11am",
        "title": "Next Monday · 11:00 AM – 11:30 AM (EST)",
        "date_label": "Monday",
        "time_label": "11:00 AM",
        "duration": "30 mins",
        "specialist": "David Chen",
        "role": "Enterprise SharePoint Consultant",
        "status": "available",
    },
]


def get_preferred_timeslots() -> list[dict]:
    return PREFERRED_TIMESLOTS


def dispatch_sms(
    workspace_id: str,
    to_phone: str,
    body: str,
    lead_id: str | None = None,
    call_id: str | None = None,
    campaign_id: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """
    Sends an SMS message. If Twilio environment variables are configured,
    attempts live delivery; otherwise gracefully records a successful simulated delivery.
    """
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_from = os.getenv("TWILIO_PHONE_NUMBER", "+1 (555) 789-0199")

    channel = "simulated"
    gateway_status = "delivered"
    gateway_id = f"sms_sim_{new_id('')}"

    if twilio_sid and twilio_token and twilio_from:
        try:
            import httpx

            url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
            resp = httpx.post(
                url,
                data={"To": to_phone, "From": twilio_from, "Body": body},
                auth=(twilio_sid, twilio_token),
                timeout=5.0,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                channel = "twilio"
                gateway_status = data.get("status", "sent")
                gateway_id = data.get("sid", gateway_id)
            else:
                log.warning("Twilio SMS send returned %s: %s", resp.status_code, resp.text)
        except Exception as e:
            log.warning("Twilio SMS dispatch failed: %s, falling back to simulated log", e)

    sms_record = create_record(
        "sms_logs",
        {
            "id": new_id("sms"),
            "workspace_id": workspace_id,
            "lead_id": lead_id,
            "call_id": call_id,
            "campaign_id": campaign_id,
            "to_phone": to_phone,
            "from_phone": twilio_from,
            "body": body,
            "status": gateway_status,
            "delivery_channel": channel,
            "gateway_message_id": gateway_id,
            "sent_at": utcnow(),
            "created_at": utcnow(),
            "metadata": metadata or {},
        },
    )

    return sms_record


def send_calendly_sms(
    workspace_id: str,
    lead_id: str,
    call_id: str | None = None,
    campaign_id: str | None = None,
    to_phone: str | None = None,
    custom_link: str | None = None,
) -> dict:
    """
    Sends a text message with the Calendly booking link when a lead requests a human.
    Creates or links a calendly_bookings tracking record.
    """
    lead = get_by_id("leads", lead_id) or {}
    contact_phone = to_phone or lead.get("phone") or "+1 (555) 349-2810"
    company_name = lead.get("company") or "there"
    contact_name = lead.get("name") or company_name

    booking_id = new_id("cal_bk")
    calendly_link = _build_calendly_link(lead_id, booking_id)

    # Create Calendly booking tracking record
    booking_record = create_record(
        "calendly_bookings",
        {
            "id": booking_id,
            "workspace_id": workspace_id,
            "lead_id": lead_id,
            "call_id": call_id,
            "campaign_id": campaign_id,
            "contact_name": contact_name,
            "contact_email": lead.get("email") or "",
            "company": lead.get("company"),
            "phone": contact_phone,
            "calendly_link": calendly_link,
            "delivery_channel": "simulated_sms",
            "status": "pending_booking",  # "pending_booking" | "booked" | "recalled"
            "preferred_slots": PREFERRED_TIMESLOTS,
            "created_at": utcnow(),
            "last_checked_at": utcnow(),
            "recalled_at": None,
            "booked_at": None,
            "booking_details": None,
        },
    )

    # Compose SMS — short, personal, direct
    sms_body = (
        f"Hi {contact_name}! A Northwind Digital specialist is ready for your call. "
        f"Pick your preferred time here: {calendly_link}"
    )

    # Send SMS
    sms_log = dispatch_sms(
        workspace_id=workspace_id,
        to_phone=contact_phone,
        body=sms_body,
        lead_id=lead_id,
        call_id=call_id,
        campaign_id=campaign_id,
        metadata={
            "booking_id": booking_id,
            "calendly_link": calendly_link,
            "type": "human_handoff_calendly_link",
        },
    )

    # Update call record if present
    if call_id:
        update_record(
            "calls",
            call_id,
            {
                "sms_sent": True,
                "sms_id": sms_log["id"],
                "calendly_link": calendly_link,
                "calendly_status": "pending_booking",
                "calendly_booking_id": booking_id,
                "handoff_action": "sms_calendly_link_dispatched",
            },
        )

    # Create team notification
    create_record(
        "notifications",
        {
            "id": new_id("ntf"),
            "workspace_id": workspace_id,
            "type": "calendly_sms_sent",
            "title": "📱 SMS Sent: Calendly Link Dispatched",
            "body": f"Texted Calendly booking link to {contact_name} ({company_name}, {contact_phone}) for human specialist handoff.",
            "opportunity_id": lead.get("opportunity_id"),
            "read": False,
            "is_demo": True,
            "created_at": utcnow(),
        },
    )

    return {
        "booking": booking_record,
        "sms": sms_log,
        "calendly_link": calendly_link,
        "phone": contact_phone,
        "body": sms_body,
    }


def complete_calendly_booking(
    workspace_id: str,
    booking_id: str | None = None,
    lead_id: str | None = None,
    slot_id: str | None = None,
    slot_title: str | None = None,
    specialist: str | None = None,
    notes: str = "",
    user_name: str | None = None,
) -> dict:
    """
    Marks a Calendly booking as booked, updates the lead to 'meeting_scheduled',
    clears any pending auto-recalls, and logs confirmation tasks and notifications.
    """
    booking = None
    if booking_id:
        booking = get_by_id("calendly_bookings", booking_id)
    if not booking and lead_id:
        # Find latest pending booking for this lead
        all_bookings = [
            b for b in by_workspace("calendly_bookings", workspace_id)
            if b.get("lead_id") == lead_id
        ]
        if all_bookings:
            booking = sorted(all_bookings, key=lambda x: x.get("created_at") or "", reverse=True)[0]

    lead_id = lead_id or (booking.get("lead_id") if booking else None)
    lead = get_by_id("leads", lead_id) if lead_id else {}

    # Identify slot
    matched_slot = next((s for s in PREFERRED_TIMESLOTS if s["id"] == slot_id), None)
    confirmed_title = slot_title or (matched_slot["title"] if matched_slot else "Today · 2:00 PM – 2:30 PM (EST)")
    confirmed_specialist = specialist or (matched_slot["specialist"] if matched_slot else "Sarah Jenkins (Solutions Architect)")

    details = {
        "slot_id": slot_id or (matched_slot["id"] if matched_slot else "slot_custom"),
        "timeslot": confirmed_title,
        "specialist": confirmed_specialist,
        "notes": notes,
        "booked_at": utcnow(),
    }

    if booking:
        booking = update_record(
            "calendly_bookings",
            booking["id"],
            {
                "status": "booked",
                "booked_at": utcnow(),
                "booking_details": details,
            },
        )
    else:
        booking = create_record(
            "calendly_bookings",
            {
                "id": booking_id or new_id("cal_bk"),
                "workspace_id": workspace_id,
                "lead_id": lead_id,
                "company": (lead or {}).get("company"),
                "phone": (lead or {}).get("phone"),
                "status": "booked",
                "booked_at": utcnow(),
                "booking_details": details,
                "created_at": utcnow(),
            },
        )

    # Update Lead in CRM to Meeting Scheduled
    if lead_id and lead:
        update_record(
            "leads",
            lead_id,
            {
                "pipeline_stage": "meeting_scheduled",
                "qualification_status": "complete",
                "intent_level": "Interested",
                "calendly_booked": True,
                "calendly_slot": confirmed_title,
                "last_updated": utcnow(),
            },
        )

    # Update call if linked
    if booking.get("call_id"):
        update_record(
            "calls",
            booking["call_id"],
            {
                "calendly_status": "booked",
                "calendly_slot": confirmed_title,
            },
        )

    # Create Follow-up Meeting Task
    due_date = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()
    company_title = (lead or {}).get("company") or "Lead"
    task = create_record(
        "tasks",
        {
            "id": new_id("task"),
            "workspace_id": workspace_id,
            "title": f"Calendly Call: {company_title} with {confirmed_specialist}",
            "priority": "HIGH",
            "due": due_date,
            "reason": f"Confirmed booking via Calendly for {confirmed_title}. {notes}".strip(),
            "status": "open",
            "assignee": user_name or "Sarah Jenkins",
            "lead_id": lead_id,
            "opportunity_id": (lead or {}).get("opportunity_id"),
            "created_at": utcnow(),
            "is_demo": True,
        },
    )

    # Create Notification
    create_record(
        "notifications",
        {
            "id": new_id("ntf"),
            "workspace_id": workspace_id,
            "type": "calendly_booked",
            "title": "🎉 Calendly Call Confirmed!",
            "body": f"{company_title} booked {confirmed_title} with {confirmed_specialist}.",
            "opportunity_id": (lead or {}).get("opportunity_id"),
            "read": False,
            "is_demo": True,
            "created_at": utcnow(),
        },
    )

    return {
        "ok": True,
        "booking": booking,
        "details": details,
        "task": task,
    }


def _get_calendly_token() -> str:
    return os.getenv("CALENDLY_ACCESS_TOKEN", "")


def _get_calendly_event_type_uri() -> str:
    return os.getenv("CALENDLY_EVENT_TYPE_URI", "")


def _resolve_event_type_uri(token: str, user_uri: str = "") -> str:
    """
    Find the first active Calendly event_type for the authenticated user.
    Caches the result in the _meta table so we don't hit /event_types on every call.
    Falls back to CALENDLY_EVENT_TYPE_URI env var if the API call fails.
    """
    cached = _meta_get("calendly_event_type_uri")
    if cached:
        return cached

    explicit = _get_calendly_event_type_uri()
    if explicit:
        _meta_set("calendly_event_type_uri", explicit)
        return explicit

    try:
        import httpx
        me_resp = httpx.get(
            f"{CALENDLY_API}/users/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8.0,
        )
        if me_resp.status_code != 200:
            return ""
        me = me_resp.json().get("resource") or {}
        user_uri = user_uri or me.get("uri") or ""

        et_resp = httpx.get(
            f"{CALENDLY_API}/event_types",
            params={"user": user_uri, "active": "true", "count": 10},
            headers={"Authorization": f"Bearer {token}"},
            timeout=8.0,
        )
        if et_resp.status_code != 200:
            log.warning("Calendly event_types fetch failed: %s %s", et_resp.status_code, et_resp.text[:200])
            return ""
        collection = et_resp.json().get("collection") or []
        if not collection:
            return ""
        uri = collection[0].get("uri") or ""
        if uri:
            _meta_set("calendly_event_type_uri", uri)
        return uri
    except Exception as exc:
        log.warning("Calendly event_type resolution failed: %s", exc)
        return ""


def _create_calendly_event(
    token: str,
    event_type_uri: str,
    invitee_name: str,
    invitee_email: str,
    start_time_iso: str,
    end_time_iso: str | None = None,
    booking_ref: str = "",
) -> dict:
    """
    POST /scheduled_events — creates a Calendly event on behalf of an invitee.
    Calendly fires the standard confirmation email to `invitee_email`.
    Requires scope: scheduled_events:write.
    """
    try:
        import httpx
        payload: dict = {
            "event_type": event_type_uri,
            "invitee": {
                "email": invitee_email,
                "name": invitee_name or invitee_email,
            },
        }
        if booking_ref:
            payload["invitee"]["tracking"] = {
                "utm_source": booking_ref,
                "utm_content": booking_ref,
            }
        if end_time_iso:
            payload["end_time"] = end_time_iso

        resp = httpx.post(
            f"{CALENDLY_API}/scheduled_events",
            json=payload,
            params={"start_time": start_time_iso} if not end_time_iso else None,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )
        if resp.status_code in (200, 201):
            resource = resp.json().get("resource") or {}
            return {
                "ok": True,
                "event_uri": resource.get("uri"),
                "invitee_uri": (resource.get("invitee_counter") or "") if False else None,
                "raw": resource,
            }
        return {
            "ok": False,
            "status": resp.status_code,
            "error": resp.text[:400],
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def schedule_callback(
    workspace_id: str,
    lead_id: str,
    parsed: dict,
    call_id: str | None = None,
    campaign_id: str | None = None,
    specialist: str | None = None,
    raw_user_text: str | None = None,
) -> dict:
    """
    Create a Calendly 'pending_booking' row for a callback the prospect explicitly
    requested by time (e.g. 'call me tomorrow at 11 AM').

    Confirmation strategy:
      1. If CALENDLY_ACCESS_TOKEN is set AND the lead has an email address,
         POST /scheduled_events to create a real Calendly event on the lead's behalf.
         Calendly fires its built-in confirmation email to the lead automatically.
      2. Otherwise (or if the API call fails / scope missing), fall back to
         Twilio SMS so the lead still gets the Calendly link.
    """
    lead = get_by_id("leads", lead_id) or {}
    contact_phone = lead.get("phone") or ""
    contact_email_original = lead.get("email") or ""
    contact_email = _resolve_send_email(contact_email_original)
    contact_name = lead.get("name") or lead.get("company") or "there"
    company = lead.get("company") or ""

    booking_id = new_id("cal_bk")
    calendly_link = _build_calendly_link(lead_id, booking_id, {
        "a1": "time_requested",
        "a2": parsed["date"],
        "a3": parsed["time"],
    })

    slot_title = parsed["label"]
    chosen_specialist = specialist or "Sarah Jenkins (Solutions Architect)"

    # ── Attempt Calendly API (fires built-in confirmation email) ─────────
    calendly_api_result = {"ok": False, "skipped": True, "reason": "not_attempted"}
    token = _get_calendly_token()
    if token and contact_email:
        event_type_uri = _resolve_event_type_uri(token)
        if event_type_uri:
            start_iso = parsed["datetime"]
            try:
                start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
                end_iso = (start_dt + timedelta(minutes=30)).isoformat().replace("+00:00", "Z")
            except Exception:
                end_iso = None
            calendly_api_result = _create_calendly_event(
                token=token,
                event_type_uri=event_type_uri,
                invitee_name=contact_name,
                invitee_email=contact_email,
                start_time_iso=start_iso,
                end_time_iso=end_iso,
                booking_ref=booking_id,
            )
            if not calendly_api_result.get("ok"):
                log.warning(
                    "Calendly scheduled_events create failed (%s): %s — falling back to SMS",
                    calendly_api_result.get("status"),
                    calendly_api_result.get("error"),
                )
        else:
            calendly_api_result = {"ok": False, "skipped": True, "reason": "no_event_type"}
    else:
        calendly_api_result = {
            "ok": False,
            "skipped": True,
            "reason": "missing_token_or_email" if not token else "missing_email",
        }

    delivery_channel = "calendly_email" if calendly_api_result.get("ok") else "simulated_sms"

    booking_record = create_record(
        "calendly_bookings",
        {
            "id": booking_id,
            "workspace_id": workspace_id,
            "lead_id": lead_id,
            "call_id": call_id,
            "campaign_id": campaign_id,
            "contact_name": contact_name,
            "contact_email": contact_email,
            "lead_email_original": contact_email_original,
            "company": company,
            "phone": contact_phone,
            "calendly_link": calendly_link,
            "status": "booked" if calendly_api_result.get("ok") else "pending_booking",
            "preferred_slots": PREFERRED_TIMESLOTS,
            "requested_slot": {
                "date": parsed["date"],
                "time": parsed["time"],
                "label": slot_title,
                "specialist": chosen_specialist,
                "raw_user_text": raw_user_text or parsed["raw"],
                "requested_at": utcnow(),
            },
            "calendly_event_uri": calendly_api_result.get("event_uri"),
            "delivery_channel": delivery_channel,
            "created_at": utcnow(),
            "last_checked_at": utcnow(),
            "recalled_at": None,
            "booked_at": utcnow() if calendly_api_result.get("ok") else None,
            "booking_details": (
                {"event_uri": calendly_api_result.get("event_uri"), "via": "calendly_api"}
                if calendly_api_result.get("ok")
                else None
            ),
        },
    )

    # ── Fallback / supplemental SMS ──────────────────────────────────────
    sms_log = None
    if not calendly_api_result.get("ok") and contact_phone:
        sms_body = (
            f"Hi {contact_name}! Per your request, a Northwind Digital specialist will call you at "
            f"{slot_title}. Confirm or pick a different slot here: {calendly_link}"
        )
        sms_log = dispatch_sms(
            workspace_id=workspace_id,
            to_phone=contact_phone,
            body=sms_body,
            lead_id=lead_id,
            call_id=call_id,
            campaign_id=campaign_id,
            metadata={
                "booking_id": booking_id,
                "calendly_link": calendly_link,
                "requested_slot": parsed,
                "type": "callback_scheduled",
                "reason": calendly_api_result.get("reason") or calendly_api_result.get("error", "fallback"),
            },
        )
    elif not calendly_api_result.get("ok") and not contact_phone:
        sms_log = {"id": new_id("sms"), "status": "no_phone_no_email", "delivery_channel": "skipped"}

    if call_id:
        update_record(
            "calls",
            call_id,
            {
                "sms_sent": bool(sms_log and sms_log.get("status") not in ("no_phone_no_email",)),
                "sms_id": sms_log["id"] if isinstance(sms_log, dict) and sms_log.get("id") else None,
                "calendly_link": calendly_link,
                "calendly_status": booking_record["status"],
                "calendly_booking_id": booking_id,
                "calendly_event_uri": calendly_api_result.get("event_uri"),
                "handoff_action": "callback_scheduled",
                "requested_slot": parsed,
            },
        )

    if lead_id and lead:
        new_stage = "meeting_scheduled" if calendly_api_result.get("ok") else "callback_scheduled"
        update_record(
            "leads",
            lead_id,
            {
                "pipeline_stage": new_stage,
                "intent_level": "Interested",
                "qualification_status": "complete" if calendly_api_result.get("ok") else "in_progress",
                "calendly_booked": bool(calendly_api_result.get("ok")),
                "calendly_slot": slot_title,
                "requested_slot": parsed,
                "last_updated": utcnow(),
            },
        )

    create_record(
        "tasks",
        {
            "id": new_id("task"),
            "workspace_id": workspace_id,
            "title": f"Callback: {company or contact_name} at {slot_title}",
            "priority": "HIGH",
            "due": parsed["date"],
            "reason": (
                f"Calendly event created ({calendly_api_result.get('event_uri')}). "
                f"Confirmation email sent to {contact_email}."
                if calendly_api_result.get("ok")
                else f"Lead requested callback at {slot_title}. Raw: {(raw_user_text or parsed['raw'])[:200]}"
            ),
            "status": "open",
            "assignee": chosen_specialist,
            "lead_id": lead_id,
            "opportunity_id": lead.get("opportunity_id"),
            "created_at": utcnow(),
            "is_demo": True,
        },
    )

    if calendly_api_result.get("ok"):
        notification_body = (
            f"{contact_name} ({company}) booked {slot_title} via Calendly API. "
            f"Confirmation email sent to {contact_email}. Event: {calendly_api_result.get('event_uri')}"
        )
        notification_title = f"✉️ Calendly Email Sent: {slot_title}"
    else:
        reason = calendly_api_result.get("reason") or calendly_api_result.get("error", "fallback")
        notification_body = (
            f"{contact_name} ({company}) requested a callback at {slot_title}. "
            f"Calendly API unavailable ({reason}); SMS link dispatched."
            if contact_phone
            else f"{contact_name} ({company}) requested a callback at {slot_title}. "
                 f"Calendly API unavailable ({reason}); no phone on file for fallback."
        )
        notification_title = f"📅 Callback Scheduled: {slot_title}"

    create_record(
        "notifications",
        {
            "id": new_id("ntf"),
            "workspace_id": workspace_id,
            "type": "callback_scheduled",
            "title": notification_title,
            "body": notification_body,
            "opportunity_id": lead.get("opportunity_id"),
            "read": False,
            "is_demo": True,
            "created_at": utcnow(),
        },
    )

    return {
        "booking": booking_record,
        "sms": sms_log,
        "calendly_link": calendly_link,
        "calendly_event_uri": calendly_api_result.get("event_uri"),
        "delivery_channel": delivery_channel,
        "phone": contact_phone,
        "email": contact_email,
        "lead_email_original": contact_email_original,
        "email_overridden": bool((os.getenv("DEFAULT_LEAD_EMAIL", DEFAULT_LEAD_EMAIL) or "").strip()) and contact_email != contact_email_original,
        "parsed": parsed,
    }


def check_unbooked_and_recall(
    workspace_id: str,
    campaign_id: str | None = None,
    lead_id: str | None = None,
    force_immediate: bool = True,
    user: dict | None = None,
) -> list[dict]:
    """
    Core Tracking & Auto-Recall Logic:
    Later on, tracks if the lead has booked the link via Calendly or not.
    If it has not been booked, the AI initiates another call to that lead to follow up.
    """
    user_name = (user or {}).get("name") or "AI Automation"
    bookings = by_workspace("calendly_bookings", workspace_id)
    candidates = [b for b in bookings if b.get("status") == "pending_booking"]

    if lead_id:
        candidates = [b for b in candidates if b.get("lead_id") == lead_id]
    if campaign_id:
        candidates = [b for b in candidates if b.get("campaign_id") == campaign_id or not b.get("campaign_id")]

    recall_results: list[dict] = []

    for bk in candidates:
        lid = bk.get("lead_id")
        lead = get_by_id("leads", lid) if lid else None
        if not lead:
            continue

        cid = bk.get("campaign_id") or campaign_id
        campaign = get_by_id("campaigns", cid) if cid else None
        if not campaign:
            camps = by_workspace("campaigns", workspace_id)
            campaign = camps[0] if camps else None
            cid = campaign.get("id") if campaign else None

        agent_id = campaign.get("agent_id") if campaign else None
        agent = get_by_id("voice_agents", agent_id) if agent_id else None
        if not agent:
            agents = by_workspace("voice_agents", workspace_id)
            agent = agents[0] if agents else {
                "id": "agent_default",
                "name": "Alex",
                "approved_voicemail": "Please call us back.",
            }

        loc = bk.get("language") or (campaign.get("language") if campaign else "en") or "en"
        s = scripts(loc)
        recall_script = s.get("calendly_recall") or s.get("handoff")

        # Execute Follow-up AI Call
        call_id = new_id("call")
        recall_call = create_record(
            "calls",
            {
                "id": call_id,
                "workspace_id": workspace_id,
                "campaign_id": cid,
                "lead_id": lid,
                "opportunity_id": lead.get("opportunity_id"),
                "agent_id": agent.get("id"),
                "mode": "demo",
                "label": "Demo Voice Simulation",
                "outcome": "Connected",
                "duration_sec": 38,
                "language": loc,
                "is_recall": True,
                "recall_reason": "unbooked_calendly_link",
                "escalated": False,
                "sms_sent": True,
                "calendly_status": "recalled",
                "calendly_booking_id": bk["id"],
                "started_at": utcnow(),
                "is_demo": True,
            },
        )

        # Build realistic conversation turns for the re-dial
        turns = [
            {"speaker": "prospect", "text": "Hello? Who is this?", "ts": utcnow()},
            {"speaker": "agent", "text": recall_script, "ts": utcnow()},
            {
                "speaker": "prospect",
                "text": "Oh, thanks for following up! Yes, I got the text message earlier, just got caught in a meeting. Let me look at the slots right now.",
                "ts": utcnow(),
            },
            {
                "speaker": "agent",
                "text": "Sounds great! The link has all our team's open slots. We look forward to connecting with you.",
                "ts": utcnow(),
            },
        ]

        create_record(
            "transcripts",
            {
                "id": new_id("tr"),
                "workspace_id": workspace_id,
                "call_id": call_id,
                "turns": turns,
                "summary": (
                    f"Auto follow-up re-call completed for {lead.get('company')}. "
                    "Lead was texted a Calendly link earlier but had not completed booking. "
                    "Lead confirmed receipt of link and agreed to select a preferred timeslot."
                ),
                "requirements": "SharePoint migration consultation",
                "interest_level": "Interested",
                "recommended_action": {
                    "action": "Awaiting timeslot selection from re-sent Calendly link",
                    "channel": "calendly",
                },
            },
        )

        create_record(
            "qualifications",
            {
                "id": new_id("qual"),
                "workspace_id": workspace_id,
                "call_id": call_id,
                "lead_id": lid,
                "opportunity_id": lead.get("opportunity_id"),
                "interest_level": "Interested",
                "requirements": "SharePoint migration support",
                "timeline": "active follow-up",
                "budget": None,
                "high_intent": True,
                "banner": "RE-CALLED: UNBOOKED CALENDLY FOLLOW-UP",
                "banner_reason": "Lead prompted after unbooked Calendly link",
                "created_at": utcnow(),
                "is_demo": True,
            },
        )

        # Update the Calendly booking tracking state
        update_record(
            "calendly_bookings",
            bk["id"],
            {
                "status": "recalled",
                "recalled_at": utcnow(),
                "recall_call_id": call_id,
            },
        )

        # Update Campaign lead attempts and timeline if campaign exists
        if campaign and cid:
            attempts = dict(campaign.get("lead_attempts") or {})
            row = dict(attempts.get(lid) or {"count": 1, "timeline": []})
            row["count"] = int(row.get("count") or 1) + 1
            row.setdefault("timeline", []).append(
                {
                    "attempt": row["count"],
                    "outcome": "Connected (Calendly Follow-up Re-dial)",
                    "at": utcnow(),
                    "retry_scheduled": False,
                    "recall": True,
                }
            )
            attempts[lid] = row
            c_timeline = list(campaign.get("timeline") or [])
            c_timeline.append({
                "lead_id": lid,
                "attempt": row["count"],
                "outcome": "Connected (Calendly Follow-up Re-dial)",
                "at": utcnow(),
                "recall": True,
            })
            update_record("campaigns", cid, {"lead_attempts": attempts, "timeline": c_timeline})

        # Create Task & Notification
        create_record(
            "notifications",
            {
                "id": new_id("ntf"),
                "workspace_id": workspace_id,
                "type": "calendly_auto_recall",
                "title": "📞 Auto Re-call Executed: Calendly Follow-up",
                "body": (
                    f"Lead {lead.get('company')} was re-dialed automatically because they hadn't booked "
                    "via the texted Calendly link. Call connected successfully and prospect confirmed receipt."
                ),
                "opportunity_id": lead.get("opportunity_id"),
                "read": False,
                "is_demo": True,
                "created_at": utcnow(),
            },
        )

        recall_results.append({
            "lead_id": lid,
            "company": lead.get("company"),
            "call_id": call_id,
            "booking_id": bk["id"],
            "status": "recalled",
            "message": "AI successfully re-dialed prospect following unbooked Calendly link.",
        })

    return recall_results
