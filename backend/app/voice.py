from __future__ import annotations

from datetime import timedelta

from app.knowledge import knowledge_store
from app.store import by_workspace, get_by_id, utcnow


DISCLOSURE = (
    "Hello, I am an AI sales assistant calling on behalf of Northwind Digital. "
    "This is a demo voice simulation. I can share only approved service information."
)

HANDOFF = ["speak to a human", "transfer", "real person", "specialist please", "handoff"]
OPT_OUT = ["do not call", "don't call", "remove me", "opt out", "stop calling", "not interested in calls"]


def _kb(agent: dict, query: str) -> str:
    docs = agent.get("knowledge_doc_ids") or []
    chunks = knowledge_store.search(agent["workspace_id"], query, docs)
    return chunks[0] if chunks else ""


def detect_interest(user_text: str) -> str:
    t = user_text.lower()
    if any(p in t for p in OPT_OUT) or "not interested" in t:
        return "Not Interested"
    if "voicemail" in t:
        return "Unknown"
    if "callback" in t or "call me back" in t or "call back" in t:
        return "Callback"
    if "demo" in t:
        return "Demo Requested"
    if "proposal" in t:
        return "Proposal Requested"
    if "meeting" in t:
        return "Meeting Requested"
    if any(w in t for w in ["interested", "want to start", "this month", "looking for sharepoint", "migration support"]):
        return "Interested"
    return "Unknown"


def agent_reply(agent: dict, user_text: str, history: list[dict], locale: str = "en") -> dict:
    t = user_text.lower()
    interest = detect_interest(user_text)
    stop_reason = None
    escalated = False
    outcome = None

    if any(p in t for p in OPT_OUT) or "not interested" in t:
        reply = "Understood. I will stop outreach and add this number to the do-not-contact list. Thank you."
        stop_reason = "opt_out_or_not_interested"
        outcome = "Not Interested"
        interest = "Not Interested"
    elif any(p in t for p in HANDOFF):
        reply = "I am connecting you with a human specialist. I will create a high-priority follow-up task now."
        stop_reason = "human_handoff"
        escalated = True
        outcome = "Callback Requested"
        interest = "Callback"
    elif "internal it" in t or "we already have" in t:
        reply = (
            "That is common. Northwind Digital often works alongside an internal IT team on SharePoint implementation "
            "and migration. Would you like a specialist to discuss a co-delivery model?"
        )
    elif "how much" in t or "cost" in t or "price" in t:
        kb = _kb(agent, "pricing")
        reply = (
            "I do not have approved public pricing. Pricing is scoped after discovery. "
            "I can arrange a human specialist to discuss a workshop. " + (kb[:180] if kb else "")
        )
    elif "what services" in t or "services do you" in t:
        reply = (
            "We provide SharePoint implementation, SharePoint migration, Microsoft 365 consulting, "
            "customization, integration, and enterprise document management — based on approved knowledge."
        )
    elif "voicemail" in t or t.strip() == "":
        reply = agent.get("approved_voicemail") or "Please call us back regarding SharePoint services."
        outcome = "Voicemail"
    elif interest in ("Interested", "Proposal Requested", "Meeting Requested", "Demo Requested"):
        reply = (
            "Thank you. I have noted a high-intent requirement for SharePoint support. "
            "A specialist should follow up to schedule a meeting and discuss a proposal. "
            "Is there anything else I should capture about timeline or technology?"
        )
        outcome = "Interested"
    elif interest == "Callback":
        reply = "I will schedule a callback with a human salesperson. When is a good time?"
        outcome = "Callback Requested"
    else:
        reply = (
            "I can help qualify SharePoint and Microsoft 365 needs using approved company information. "
            "What service are you looking for, and what is your timeline?"
        )

    if locale == "hi":
        reply = "मैं नॉर्थविंड डिजिटल की AI सहायक हूँ। " + reply
    elif locale == "gu":
        reply = "હું નોર્થવિન્ડ ડિજિટલની AI સહાયક છું. " + reply

    qual = {
        "interest_level": interest,
        "requirements": "SharePoint migration support" if "sharepoint" in t or "migration" in t else None,
        "timeline": "this month" if "this month" in t else None,
        "budget": None,
        "technology": "SharePoint" if "sharepoint" in t else None,
        "decision_stage": "active requirement" if interest == "Interested" else "unknown",
        "missing_information": [] if interest == "Interested" else ["Budget"],
        "evidence": [{"quote": user_text, "source": "Demo Voice Simulation"}],
        "high_intent": interest in ("Interested", "Proposal Requested", "Meeting Requested", "Demo Requested"),
    }
    if qual["high_intent"]:
        qual["banner"] = "HIGH INTENT PROSPECT"
        qual["banner_reason"] = user_text

    return {
        "reply": reply,
        "disclosure_used": True,
        "mode": "demo_simulation",
        "interest": interest,
        "qualification": qual,
        "stop_reason": stop_reason,
        "escalated": escalated,
        "outcome": outcome,
        "history": history
        + [
            {"speaker": "prospect", "text": user_text, "ts": utcnow()},
            {"speaker": "agent", "text": reply, "ts": utcnow()},
        ],
    }


def opening_message(agent: dict, locale: str = "en") -> str:
    msg = DISCLOSURE + " " + (agent.get("call_objective") or "")
    if locale == "hi":
        return "नमस्ते, मैं एक AI एजेंट हूँ। " + msg
    if locale == "gu":
        return "નમસ્તે, હું એક AI એજન્ટ છું. " + msg
    return msg


class DemoVoiceProvider:
    label = "Demo Voice Simulation"

    def reply(self, agent, user_text, history, locale="en"):
        return agent_reply(agent, user_text, history, locale)


class LiveVoiceProvider:
    label = "Live voice"

    def reply(self, agent, user_text, history, locale="en"):
        raise RuntimeError("Live telephony/STT/TTS is not configured. Use DEMO MODE.")


demo_voice = DemoVoiceProvider()
live_voice = LiveVoiceProvider()
