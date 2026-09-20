from __future__ import annotations

from app.knowledge import knowledge_store
from app.store import utcnow


HANDOFF = ["speak to a human", "transfer", "real person", "specialist please", "handoff", "इंसान", "માનવ"]
OPT_OUT = ["do not call", "don't call", "remove me", "opt out", "stop calling", "not interested in calls"]

SCRIPTS = {
    "en": {
        "disclosure": (
            "Hello, I am an AI sales assistant calling on behalf of Northwind Digital. "
            "This is a demo voice simulation. I can share only approved service information."
        ),
        "greeting": "Could you tell me how your team currently manages SharePoint?",
        "qualify": "What SharePoint or Microsoft 365 outcome are you trying to achieve, and what is the timeline?",
        "faq_services": (
            "We provide SharePoint implementation, SharePoint migration, Microsoft 365 consulting, "
            "customization, integration, and enterprise document management — based on approved knowledge."
        ),
        "faq_price": "I do not have approved public pricing. Pricing is scoped after discovery. I can arrange a human specialist to discuss a workshop.",
        "internal_it": (
            "That is common. Northwind Digital often works alongside an internal IT team on SharePoint implementation "
            "and migration. Would you like a specialist to discuss a co-delivery model?"
        ),
        "interested": (
            "Thank you. I have noted a high-intent requirement for SharePoint support. "
            "A specialist should follow up to schedule a meeting and discuss a proposal."
        ),
        "callback": "I will schedule a callback with a human salesperson. When is a good time?",
        "not_interested": "Understood. I will stop outreach and add this number to the do-not-contact list. Thank you.",
        "handoff": "I am connecting you with a human specialist. I will create a high-priority follow-up task now.",
        "voicemail": "Hello, this is an AI assistant from Northwind Digital. Please call us back regarding SharePoint services. This is a demo simulation.",
        "closing": "Thank you for your time. A human teammate will follow the next best action we captured.",
        "fallback": "I can help qualify SharePoint and Microsoft 365 needs using approved company information. What service are you looking for, and what is your timeline?",
        "no_answer": "No answer. Retry is eligible under the demo campaign policy.",
        "connected": "The call connected. I will continue qualification using approved knowledge only.",
    },
    "hi": {
        "disclosure": "नमस्ते, मैं नॉर्थविंड डिजिटल की AI सेल्स सहायक हूँ। यह डेमो वॉइस सिमुलेशन है। मैं केवल स्वीकृत जानकारी साझा कर सकती हूँ।",
        "greeting": "क्या आप बता सकते हैं कि आपकी टीम वर्तमान में SharePoint को कैसे मैनेज करती है?",
        "qualify": "आप SharePoint या Microsoft 365 में क्या परिणाम चाहते हैं, और समयसीमा क्या है?",
        "faq_services": "स्वीकृत ज्ञान के अनुसार हम SharePoint इम्प्लीमेंटेशन, माइग्रेशन, Microsoft 365 कंसल्टिंग, कस्टमाइज़ेशन, इंटीग्रेशन और डॉक्यूमेंट मैनेजमेंट देते हैं।",
        "faq_price": "मेरे पास स्वीकृत सार्वजनिक मूल्य नहीं है। मूल्य डिस्कवरी के बाद तय होता है। मैं एक मानव विशेषज्ञ से कार्यशाला की चर्चा करा सकती हूँ।",
        "internal_it": "यह आम है। नॉर्थविंड डिजिटल अक्सर आंतरिक IT टीम के साथ SharePoint इम्प्लीमेंटेशन और माइग्रेशन करता है। क्या कोई विशेषज्ञ सह-डिलीवरी पर बात करे?",
        "interested": "धन्यवाद। मैंने SharePoint सहायता की उच्च-इंटेंट आवश्यकता दर्ज कर ली है। एक विशेषज्ञ मीटिंग और प्रस्ताव के लिए फॉलो-अप करेगा।",
        "callback": "मैं एक मानव सेल्सपर्सन के साथ कॉलबैक शेड्यूल करूँगी। अच्छा समय कब है?",
        "not_interested": "समझ गई। मैं आउटरीच रोक दूँगी और इस नंबर को डू-नॉट-कॉन्टैक्ट सूची में डाल दूँगी। धन्यवाद।",
        "handoff": "मैं आपको एक मानव विशेषज्ञ से जोड़ रही हूँ। अभी एक उच्च-प्राथमिकता फॉलो-अप टास्क बनेगा।",
        "voicemail": "नमस्ते, मैं नॉर्थविंड डिजिटल की AI सहायक हूँ। कृपया SharePoint सेवाओं के बारे में हमें वापस कॉल करें। यह डेमो सिमुलेशन है।",
        "closing": "आपके समय के लिए धन्यवाद। अगली कार्रवाई एक मानव साथी पूरी करेगा।",
        "fallback": "मैं स्वीकृत जानकारी से SharePoint और Microsoft 365 जरूरतों को क्वालिफाई कर सकती हूँ। आप कौन सी सेवा चाहते हैं, और समयसीमा क्या है?",
        "no_answer": "कोई उत्तर नहीं। डेमो कैंपेन नीति के अनुसार रीट्राई संभव है।",
        "connected": "कॉल कनेक्ट हो गई। मैं केवल स्वीकृत ज्ञान से क्वालिफिकेशन जारी रखूँगी।",
    },
    "gu": {
        "disclosure": "નમસ્તે, હું નોર્થવિન્ડ ડિજિટલની AI સેલ્સ સહાયક છું. આ ડેમો વૉઇસ સિમ્યુલેશન છે. હું માત્ર મંજૂર માહિતી શેર કરી શકું.",
        "greeting": "તમારી ટીમ હાલમાં SharePoint કેવી રીતે મેનેજ કરે છે તે વિશે તમે જણાવી શકો છો?",
        "qualify": "તમે SharePoint અથવા Microsoft 365માં શું પરિણામ ઇચ્છો છો, અને સમયમર્યાદા શું છે?",
        "faq_services": "મંજૂર જ્ઞાન મુજબ અમે SharePoint ઇમ્પ્લિમેન્ટેશન, માઇગ્રેશન, Microsoft 365 કન્સલ્ટિંગ, કસ્ટમાઇઝેશન, ઇન્ટિગ્રેશન અને ડોક્યુમેન્ટ મેનેજમેન્ટ આપીએ છીએ.",
        "faq_price": "મારી પાસે મંજૂર જાહેર કિંમત નથી. કિંમત ડિસ્કવરી પછી નક્કી થાય છે. હું માનવ નિષ્ણાત સાથે વર્કશોપની વાત કરાવી શકું.",
        "internal_it": "આ સામાન્ય છે. નોર્થવિન્ડ ડિજિટલ ઘણી વખત આંતરિક IT ટીમ સાથે SharePoint ઇમ્પ્લિમેન્ટેશન અને માઇગ્રેશન કરે છે. શું નિષ્ણાત સહ-ડિલિવરી વિશે વાત કરે?",
        "interested": "આભાર. મેં SharePoint સપોર્ટની હાઇ-ઇન્ટેન્ટ જરૂરિયાત નોંધી છે. નિષ્ણાત મીટિંગ અને પ્રસ્તાવ માટે ફોલો-અપ કરશે.",
        "callback": "હું માનવ સેલ્સપર્સન સાથે કૉલબેક શેડ્યૂલ કરીશ. સારો સમય ક્યારે છે?",
        "not_interested": "સમજાયું. હું આઉટરીચ બંધ કરીશ અને આ નંબર ડુ-નોટ-કોન્ટેક્ટ યાદીમાં મૂકીશ. આભાર.",
        "handoff": "હું તમને માનવ નિષ્ણાત સાથે જોડી રહી છું. હવે હાઇ-પ્રાયોરિટી ફોલો-અપ ટાસ્ક બનશે.",
        "voicemail": "નમસ્તે, હું નોર્થવિન્ડ ડિજિટલની AI સહાયક છું. કૃપા કરી SharePoint સેવાઓ માટે પાછા કૉલ કરો. આ ડેમો સિમ્યુલેશન છે.",
        "closing": "તમારા સમય બદલ આભાર. આગળની ક્રિયા માનવ સાથીદાર પૂર્ણ કરશે.",
        "fallback": "હું મંજૂર માહિતીથી SharePoint અને Microsoft 365 જરૂરિયાતો ક્વોલિફાય કરી શકું. તમે કઈ સેવા ઇચ્છો છો, અને સમયમર્યાદા શું છે?",
        "no_answer": "કોઈ જવાબ નથી. ડેમો કેમ્પેઇન નીતિ મુજબ રિટ્રાય શક્ય છે.",
        "connected": "કૉલ કનેક્ટ થયો. હું માત્ર મંજૂર જ્ઞાનથી ક્વોલિફિકેશન ચાલુ રાખીશ.",
    },
}


def scripts(locale: str) -> dict:
    return SCRIPTS.get(locale) or SCRIPTS["en"]


def _kb(agent: dict, query: str) -> str:
    docs = agent.get("knowledge_doc_ids") or []
    chunks = knowledge_store.search(agent["workspace_id"], query, docs)
    return chunks[0] if chunks else ""


def detect_interest(user_text: str) -> str:
    t = user_text.lower()
    if any(p in t for p in OPT_OUT) or "not interested" in t or "रुचि नहीं" in t or "રસ નથી" in t:
        return "Not Interested"
    if "voicemail" in t or "वॉइसमेल" in t:
        return "Unknown"
    if "no answer" in t or "no-answer" in t:
        return "Unknown"
    if "callback" in t or "call me back" in t or "call back" in t or "कॉलबैक" in t or "કૉલબેક" in t:
        return "Callback"
    if "demo" in t:
        return "Demo Requested"
    if "proposal" in t:
        return "Proposal Requested"
    if "meeting" in t:
        return "Meeting Requested"
    if any(w in t for w in ["interested", "want to start", "this month", "looking for sharepoint", "migration support", "रुचि", "રસ"]):
        return "Interested"
    return "Unknown"


def agent_reply(agent: dict, user_text: str, history: list[dict], locale: str = "en") -> dict:
    s = scripts(locale)
    t = user_text.lower()
    interest = detect_interest(user_text)
    stop_reason = None
    escalated = False
    outcome = None
    reply = s["fallback"]

    if "no answer" in t:
        reply = s["no_answer"]
        outcome = "No Answer"
        interest = "Unknown"
    elif any(p in t for p in OPT_OUT) or "not interested" in t or "रुचि नहीं" in user_text or "રસ નથી" in user_text:
        reply = s["not_interested"]
        stop_reason = "opt_out_or_not_interested"
        outcome = "Not Interested"
        interest = "Not Interested"
    elif any(p in t for p in HANDOFF):
        reply = s["handoff"]
        stop_reason = "human_handoff"
        escalated = True
        outcome = "Escalated"
        interest = "Callback"
    elif "internal it" in t or "we already have" in t:
        reply = s["internal_it"]
        outcome = "Connected"
    elif "how much" in t or "cost" in t or "price" in t or "कीमत" in user_text:
        kb = _kb(agent, "pricing")
        reply = s["faq_price"] + (" " + kb[:180] if kb else "")
        outcome = "Connected"
    elif "what services" in t or "services do you" in t:
        reply = s["faq_services"]
        outcome = "Connected"
    elif "voicemail" in t or t.strip() == "":
        reply = agent.get("approved_voicemail") or s["voicemail"]
        outcome = "Voicemail"
    elif "connected" == t.strip():
        reply = s["connected"] + " " + s["greeting"]
        outcome = "Connected"
    elif interest in ("Interested", "Proposal Requested", "Meeting Requested", "Demo Requested"):
        reply = s["interested"] + " " + s["closing"]
        outcome = "Interested"
    elif interest == "Callback":
        reply = s["callback"]
        outcome = "Callback Requested"
    else:
        reply = s["qualify"]
        outcome = "Connected"

    qual = {
        "interest_level": interest,
        "requirements": "SharePoint migration support" if "sharepoint" in t or "migration" in t else None,
        "timeline": "this month" if "this month" in t else None,
        "budget": None,
        "technology": "SharePoint" if "sharepoint" in t else None,
        "decision_stage": "active requirement" if interest == "Interested" else "unknown",
        "missing_information": [] if interest == "Interested" else ["Budget"],
        "evidence": [{"quote": user_text, "source": "Demo Voice Simulation"}] if user_text.strip() else [],
        "high_intent": interest in ("Interested", "Proposal Requested", "Meeting Requested", "Demo Requested"),
    }
    if qual["high_intent"]:
        qual["banner"] = "HIGH INTENT PROSPECT"
        qual["banner_reason"] = user_text

    history_out = list(history)
    if user_text.strip() and user_text.lower() != "no answer":
        history_out.append({"speaker": "prospect", "text": user_text, "ts": utcnow()})
    if outcome != "No Answer":
        history_out.append({"speaker": "agent", "text": reply, "ts": utcnow()})

    return {
        "reply": reply,
        "disclosure_used": True,
        "mode": "demo_simulation",
        "interest": interest,
        "qualification": qual,
        "stop_reason": stop_reason,
        "escalated": escalated,
        "outcome": outcome,
        "history": history_out,
    }


def opening_message(agent: dict, locale: str = "en") -> str:
    s = scripts(locale)
    extra = agent.get("call_objective") or ""
    return (s["disclosure"] + " " + s["greeting"] + (" " + extra if extra else "")).strip()


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
