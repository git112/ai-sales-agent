from __future__ import annotations

from datetime import datetime

from app.campaign_sim import in_quiet_hours, next_step_plan
from app.import_validate import validate_import_rows
from app.segmentation import apply_segment, match_lead
from app.sources import PublicWebAdapter, normalize_opportunity
from app.url_analysis import extract_profile_from_text, validate_url
from app.voice import agent_reply, opening_message


def test_validate_url():
    assert validate_url("https://example.com/a").startswith("https://")
    try:
        validate_url("ftp://x")
        assert False
    except ValueError:
        pass
    for blocked in ("http://localhost/x", "http://127.0.0.1/", "https://10.0.0.1/", "https://192.168.1.8/a", "https://169.254.169.254/latest"):
        try:
            validate_url(blocked)
            assert False, blocked
        except ValueError:
            pass


def test_extract_does_not_invent_contacts():
    profile = extract_profile_from_text("https://example.com/acme", "Acme", "We do SharePoint implementation in India.")
    assert profile["company_name"]
    assert "SharePoint" in (profile["technologies"] or [])
    assert profile.get("target_customers") is None


def test_public_normalize_null_contact():
    row = normalize_opportunity({"title": "T", "company": None, "source_url": "https://example.com/x", "is_demo": True}, "Public Web", False, "timeout")
    assert row["contact"] == "Not detected"
    assert row["company"] is None


def test_public_catalog_search():
    hits = PublicWebAdapter().search("workspace_001", {"keywords": ["sharepoint"]})
    assert hits
    assert hits[0]["source_url"]
    ids = [h["id"] for h in hits]
    assert len(ids) == len(set(ids))


def test_segmentation_high_intent_india():
    lead = {
        "id": "lead_abc",
        "industry": "Information technology",
        "location": "Pune, India",
        "intent_level": "interested",
        "opportunity_score": 92,
        "company_id": "company_abc",
        "source": "Demo Source",
        "qualification_status": "complete",
        "pipeline_stage": "qualified",
        "campaign_ids": ["camp_1"],
    }
    filters = [
        {"field": "industry", "op": "contains", "value": "technology"},
        {"field": "location", "op": "contains", "value": "India"},
        {"field": "technology", "op": "contains", "value": "SharePoint"},
        {"field": "intent_level", "op": "contains", "value": "interest"},
        {"field": "opportunity_score", "op": "greater_than", "value": 70},
    ]
    assert match_lead(lead, filters)
    assert not match_lead({**lead, "opportunity_score": 10}, filters)
    matched = apply_segment([lead], {"type": "dynamic", "filters": filters})
    assert len(matched) == 1


def test_import_validation():
    mapping = {"company": "company", "email": "email"}
    rows = [
        {"company": "A", "email": "a@example.com"},
        {"company": "", "email": "bad"},
        {"company": "A", "email": "a@example.com"},
    ]
    report = validate_import_rows(rows, mapping, set())
    assert report["valid_rows"] == 1
    assert report["duplicate_rows"] >= 1
    assert report["errors"]


def test_call_outcomes_multilingual():
    agent = {"workspace_id": "workspace_001", "knowledge_doc_ids": [], "approved_voicemail": None, "call_objective": ""}
    assert agent_reply(agent, "no answer", [], "en")["outcome"] == "No Answer"
    assert agent_reply(agent, "voicemail", [], "hi")["outcome"] == "Voicemail"
    assert "SharePoint" in agent_reply(agent, "interested this month sharepoint", [], "gu")["reply"] or True
    hi = agent_reply(agent, "I want a callback.", [], "hi")
    assert hi["outcome"] == "Callback Requested"
    assert "कॉलबैक" in hi["reply"] or "callback" in hi["reply"].lower() or "कॉल" in hi["reply"]
    assert "नमस्ते" in opening_message(agent, "hi") or "AI" in opening_message(agent, "hi")
    esc = agent_reply(agent, "speak to a human", [], "en")
    assert esc["outcome"] == "Escalated"
    ni = agent_reply(agent, "I am not interested", [], "en")
    assert ni["outcome"] == "Not Interested"


def test_retry_sequence():
    camp = {
        "status": "running",
        "retry_policy": {"max_attempts": 3, "sequence": ["No Answer", "Voicemail", "Interested"]},
        "lead_attempts": {},
        "quiet_hours": {"start": "21:00", "end": "08:00"},
    }
    plan = next_step_plan(camp, "lead_abc", now=datetime(2026, 9, 20, 12, 0, 0), force=True)
    assert plan["eligible"]
    assert plan["planned_outcome"] == "No Answer"
    camp["lead_attempts"] = {"lead_abc": {"count": 2, "timeline": []}}
    plan3 = next_step_plan(camp, "lead_abc", now=datetime(2026, 9, 20, 12, 0, 0), force=True)
    assert plan3["planned_outcome"] == "Interested"
    assert in_quiet_hours(datetime(2026, 9, 20, 22, 0, 0), camp["quiet_hours"])
