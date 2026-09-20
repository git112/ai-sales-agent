from __future__ import annotations

from pathlib import Path

from app.ai import LiveAIError, LiveAIProvider, get_ai
from app.core.config import settings
from app.db import init_db
from app.store import reset_datastore_state


def _enable_live(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test-not-real")


def test_demo_without_key_sets_ai_source_demo(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "demo")
    monkeypatch.setattr(settings, "openai_api_key", None)
    out = get_ai().understand_business(
        {"company_name": "Northwind Digital", "description": "SharePoint implementation", "services": []}
    )
    assert out["ai_source"] == "demo"
    assert "SharePoint" in out["company_summary"] or any("SharePoint" in s for s in out["services"])
    assert "openai_api_key" not in out


def test_missing_key_stays_on_demo(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", None)
    out = get_ai().understand_business({"company_name": "X", "description": "SharePoint"})
    assert out["ai_source"] == "demo"


def test_live_understand_overlay(monkeypatch):
    _enable_live(monkeypatch)

    def fake(self, payload):
        return {"company_summary": "Live summary of SharePoint services.", "services": ["SharePoint implementation"]}

    monkeypatch.setattr(LiveAIProvider, "understand_business", fake)
    out = get_ai().understand_business({"company_name": "X", "description": "SharePoint"})
    assert out["ai_source"] == "live"
    assert out["company_summary"] == "Live summary of SharePoint services."
    assert "SharePoint implementation" in out["services"]


def test_live_error_falls_back(monkeypatch):
    _enable_live(monkeypatch)

    def boom(self, payload):
        raise LiveAIError("timeout")

    monkeypatch.setattr(LiveAIProvider, "understand_business", boom)
    out = get_ai().understand_business({"company_name": "X", "description": "SharePoint"})
    assert out["ai_source"] == "demo_fallback"
    assert out["ai_fallback_reason"] == "timeout"
    assert out["services"]


def test_analyze_keeps_heuristic_scores(monkeypatch):
    _enable_live(monkeypatch)
    profile = {"services": ["SharePoint implementation"], "technologies": ["SharePoint"], "locations": ["Pune"]}
    opp = {
        "title": "SharePoint implementation partner search",
        "requirement": "Looking for a SharePoint implementation partner.",
        "need": "intranet",
        "technology": ["SharePoint"],
        "location": "Pune, India",
        "published_at": "2026-09-17T09:00:00Z",
    }
    demo_total = get_ai().demo.analyze_opportunity(profile, opp, [], [])["total"]

    def fake(self, profile, opportunity, signals, market):
        return {"why_match": "LIVE MATCH", "why_now": "LIVE NOW", "total": 1, "service_match": 1}

    monkeypatch.setattr(LiveAIProvider, "analyze_opportunity", fake)
    monkeypatch.setattr(settings, "ai_provider", "demo")
    baseline = get_ai().analyze_opportunity(profile, opp, [], [])
    monkeypatch.setattr(settings, "ai_provider", "openai")
    out = get_ai().analyze_opportunity(profile, opp, [], [])
    assert out["ai_source"] == "live"
    assert out["why_match"] == "LIVE MATCH"
    assert out["why_now"] == "LIVE NOW"
    assert out["total"] == demo_total == baseline["total"]
    assert out["service_match"] == baseline["service_match"]


def test_plan_search_and_nba_stay_demo(monkeypatch):
    _enable_live(monkeypatch)
    criteria = get_ai().plan_search("SharePoint implementation in Pune")
    assert criteria["ai_source"] == "demo"
    assert "SharePoint" in criteria["keywords"]
    nba = get_ai().next_best_action({"interest_level": "Interested"}, {})
    assert nba["ai_source"] == "demo"
    assert nba["action"] == "Schedule a human sales meeting."


def test_copilot_live_and_fallback(tmp_path: Path, monkeypatch):
    reset_datastore_state()
    settings.sqlite_path = str(tmp_path / "sales_agent.db")
    assert init_db(tmp_path / "sales_agent.db", seed=True)
    from app import store

    store._sqlite_ready = True
    _enable_live(monkeypatch)

    def fake(self, question, workspace_id):
        return {
            "answer": "ABC Technologies is the cited high-priority record.",
            "citations": [{"type": "lead", "id": "lead_abc", "label": "ABC Technologies"}],
            "grounded": True,
        }

    monkeypatch.setattr(LiveAIProvider, "copilot", fake)
    live = get_ai().copilot("Show high-intent leads.", "workspace_001")
    assert live["ai_source"] == "live"
    assert live["citations"][0]["id"] == "lead_abc"
    assert live["grounded"] is True

    def boom(self, question, workspace_id):
        raise LiveAIError("rate_limit")

    monkeypatch.setattr(LiveAIProvider, "copilot", boom)
    fb = get_ai().copilot("Show high-intent leads.", "workspace_001")
    assert fb["ai_source"] == "demo_fallback"
    assert fb["ai_fallback_reason"] == "rate_limit"
    assert fb["grounded"] is True
    assert "answer" in fb
