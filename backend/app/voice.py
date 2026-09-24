from __future__ import annotations

from app.knowledge import knowledge_store
from app.store import utcnow


HANDOFF = [
    "speak to a human", "transfer", "real person", "specialist please", "handoff",
    "इंसान", "માનવ", "hablar con una persona", "transferir", "humano", "personne humaine",
    "parler à un conseiller", "mensch", "weiterleiten", "mitarbeiter"
]
OPT_OUT = [
    "do not call", "don't call", "remove me", "opt out", "stop calling", "not interested in calls",
    "रुचि नहीं", "રસ નથી", "no me llame", "no llamar", "pas intéressé", "ne m'appelez plus",
    "nicht anrufen", "kein interesse", "abmelden"
]

SCRIPTS = {
    "en": {
        "disclosure": (
            "Hello, I am an AI sales assistant calling on behalf of Northwind Digital. "
            "I am reaching out to understand your current digital workplace initiatives."
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
        "voicemail": "Hello, this is an AI assistant from Northwind Digital. Please call us back regarding SharePoint services at your earliest convenience.",
        "closing": "Thank you for your time. A human teammate will follow the next best action we captured.",
        "fallback": "I can help qualify SharePoint and Microsoft 365 needs using approved company information. What service are you looking for, and what is your timeline?",
        "no_answer": "No answer. Follow-up task scheduled.",
        "connected": "The call connected. I will continue qualification using approved knowledge only.",
    },
    "hi": {
        "disclosure": "नमस्ते, मैं नॉर्थविंड डिजिटल की AI सेल्स सहायक हूँ। मैं आपकी डिजिटल कार्यस्थल पहलों को समझने के लिए संपर्क कर रही हूँ।",
        "greeting": "क्या आप बता सकते हैं कि आपकी टीम वर्तमान में SharePoint को कैसे मैनेज करती है?",
        "qualify": "आप SharePoint या Microsoft 365 में क्या परिणाम चाहते हैं, और समयसीमा क्या है?",
        "faq_services": "स्वीकृत ज्ञान के अनुसार हम SharePoint इम्प्लीमेंटेशन, माइग्रेशन, Microsoft 365 कंसल्टिंग, कस्टमाइज़ेशन, इंटीग्रेशन और डॉक्यूमेंट मैनेजमेंट देते हैं।",
        "faq_price": "मेरे पास स्वीकृत सार्वजनिक मूल्य नहीं है। मूल्य डिस्कवरी के बाद तय होता है। मैं एक मानव विशेषज्ञ से कार्यशाला की चर्चा करा सकती हूँ।",
        "internal_it": "यह आम है। नॉर्थविंड डिजिटल अक्सर आंतरिक IT टीम के साथ SharePoint इम्प्लीमेंटेशन और माइग्रेशन करता है। क्या कोई विशेषज्ञ सह-डिलीवरी पर बात करे?",
        "interested": "धन्यवाद। मैंने SharePoint सहायता की उच्च-इंटेंट आवश्यकता दर्ज कर ली है। एक विशेषज्ञ मीटिंग और प्रस्ताव के लिए फॉलो-अप करेगा।",
        "callback": "मैं एक मानव सेल्सपर्सन के साथ कॉलबैक शेड्यूल करूँगी। अच्छा समय कब है?",
        "not_interested": "समझ गई। मैं आउटरीच रोक दूँगी और इस नंबर को डू-नॉट-कॉन्टैक्ट सूची में डाल दूँगी। धन्यवाद।",
        "handoff": "मैं आपको एक मानव विशेषज्ञ से जोड़ रही हूँ। अभी एक उच्च-प्राथमिकता फॉलो-अप टास्क बनेगा।",
        "voicemail": "नमस्ते, मैं नॉर्थविंड डिजिटल की AI सहायक हूँ। कृपया SharePoint सेवाओं के बारे में हमें वापस कॉल करें।",
        "closing": "आपके समय के लिए धन्यवाद। अगली कार्रवाई एक मानव साथी पूरी करेगा।",
        "fallback": "मैं स्वीकृत जानकारी से SharePoint और Microsoft 365 जरूरतों को क्वालिफाई कर सकती हूँ। आप कौन सी सेवा चाहते हैं, और समयसीमा क्या है?",
        "no_answer": "कोई उत्तर नहीं। फॉलो-अप टास्क शेड्यूल कर दिया गया है।",
        "connected": "कॉल कनेक्ट हो गई। मैं केवल स्वीकृत ज्ञान से क्वालिफिकेशन जारी रखूँगी।",
    },
    "gu": {
        "disclosure": "નમસ્તે, હું નોર્થવિન્ડ ડિજિટલની AI સેલ્સ સહાયક છું. હું તમારા ડિજિટલ વર્કપ્લેસ આયોજન વિશે વાત કરવા માંગુ છું.",
        "greeting": "તમારી ટીમ હાલમાં SharePoint કેવી રીતે મેનેજ કરે છે તે વિશે તમે જણાવી શકો છો?",
        "qualify": "તમે SharePoint અથવા Microsoft 365માં શું પરિણામ ઇચ્છો છો, અને સમયમર્યાદા શું છે?",
        "faq_services": "મંજૂર જ્ઞાન મુજબ અમે SharePoint ઇમ્પ્લિમેન્ટેશન, માઇગ્રેશન, Microsoft 365 કન્સલ્ટિંગ, કસ્ટમાઇઝેશન, ઇન્ટિગ્રેશન અને ડોક્યુમેન્ટ મેનેજમેન્ટ આપીએ છીએ.",
        "faq_price": "મારી પાસે મંજૂર જાહેર કિંમત નથી. કિંમત ડિસ્કવરી પછી નક્કી થાય છે. હું માનવ નિષ્ણાત સાથે વર્કશોપની વાત કરાવી શકું.",
        "internal_it": "આ સામાન્ય છે. નોર્થવિન્ડ ડિજિટલ ઘણી વખત આંતરિક IT ટીમ સાથે SharePoint ઇમ્પ્લિમેન્ટેશન અને માઇગ્રેશન કરે છે. શું નિષ્ણાત સહ-ડિલિવરી વિશે વાત કરે?",
        "interested": "આભાર. મેં SharePoint સપોર્ટની હાઇ-ઇન્ટેન્ટ જરૂરિયાત નોંધી છે. નિષ્ણાત મીટિંગ અને પ્રસ્તાવ માટે ફોલો-અપ કરશે.",
        "callback": "હું માનવ સેલ્સપર્સન સાથે કૉલબેક શેડ્યૂલ કરીશ. સારો સમય ક્યારે છે?",
        "not_interested": "સમજાયું. હું આઉટરીચ બંધ કરીશ અને આ નંબર ડુ-નોટ-કોન્ટેક્ટ યાદીમાં મૂકીશ. આભાર.",
        "handoff": "હું તમને માનવ નિષ્ણાત સાથે જોડી રહી છું. હવે હાઇ-પ્રાયોરિટી ફોલો-અપ ટાસ્ક બનશે.",
        "voicemail": "નમસ્તે, હું નોર્થવિન્ડ ડિજિટલની AI સહાયક છું. કૃપા કરી SharePoint સેવાઓ માટે પાછા કૉલ કરો.",
        "closing": "તમારા સમય બદલ આભાર. આગળની ક્રિયા માનવ સાથીદાર પૂર્ણ કરશે.",
        "fallback": "હું મંજૂર માહિતીથી SharePoint અને Microsoft 365 જરૂરિયાતો ક્વોલિફાય કરી શકું. તમે કઈ સેવા ઇચ્છો છો, અને સમયમર્યાદા શું છે?",
        "no_answer": "કોઈ જવાબ નથી. ફોલો-અપ શેડ્યૂલ કર્યું છે.",
        "connected": "કૉલ કનેક્ટ થયો. હું માત્ર મંજૂર જ્ઞાનથી ક્વોલિફિકેશન ચાલુ રાખીશ.",
    },
    "es": {
        "disclosure": "Hola, soy una asistente de ventas con IA de Northwind Digital. Me comunico para conocer sus iniciativas de lugar de trabajo digital.",
        "greeting": "¿Podría decirme cómo gestiona su equipo actualmente SharePoint?",
        "qualify": "¿Qué resultado busca en SharePoint o Microsoft 365 y cuál es su plazo estimado?",
        "faq_services": "Brindamos implementación de SharePoint, migración, consultoría de Microsoft 365, personalizaciones y gestión documental empresarial.",
        "faq_price": "No dispongo de tarifas públicas estándar; el presupuesto se define tras el descubrimiento. Puedo coordinar un especialista para un taller.",
        "internal_it": "Es muy habitual. Northwind Digital colabora con frecuencia junto a equipos internos de TI. ¿Desea evaluar un modelo de co-entrega?",
        "interested": "Muchas gracias. He registrado un requerimiento de alta prioridad. Un especialista se comunicará para coordinar reunión y propuesta.",
        "callback": "Programaré una llamada de seguimiento con un especialista humano. ¿Qué día y horario le conviene?",
        "not_interested": "Comprendido. Detendremos el contacto y registraré su número en la lista de no contactar. Muchas gracias.",
        "handoff": "Le transferiré con un especialista humano inmediatamente. Estoy generando una tarea de seguimiento prioritaria.",
        "voicemail": "Hola, le saluda el asistente virtual de Northwind Digital. Por favor comuníquese con nosotros acerca de servicios de SharePoint.",
        "closing": "Gracias por su tiempo. Un integrante de nuestro equipo avanzará con la acción acordada.",
        "fallback": "¿Qué servicio específico de SharePoint o Microsoft 365 necesita y en qué fecha proyectan iniciar?",
        "no_answer": "Sin respuesta. Tarea de reintento programada.",
        "connected": "Llamada conectada. Continuaré la cualificación con información autorizada.",
    },
    "fr": {
        "disclosure": "Bonjour, je suis l'assistant commercial IA de Northwind Digital. Je vous contacte au sujet de vos projets d'environnement de travail numérique.",
        "greeting": "Pourriez-vous m'indiquer comment votre équipe gère actuellement SharePoint ?",
        "qualify": "Quel résultat souhaitez-vous atteindre sur SharePoint ou Microsoft 365, et sous quel délai ?",
        "faq_services": "Nous assurons le déploiement de SharePoint, la migration, le conseil Microsoft 365, l'intégration et la gestion documentaire.",
        "faq_price": "Les tarifs dépendent du cadrage technique. Je peux planifier un atelier de cadrage avec l'un de nos spécialistes.",
        "internal_it": "C'est fréquent. Northwind Digital collabore régulièrement en co-délivrance avec les équipes IT internes. Souhaitez-vous en échanger ?",
        "interested": "Merci beaucoup. J'ai bien noté votre fort intérêt. Un spécialiste vous recontactera rapidement pour organiser une présentation.",
        "callback": "Je planifie un rappel par un commercial humain. Quel moment vous conviendrait le mieux ?",
        "not_interested": "Bien noté. Nous stoppons toute démarche et ajoutons vos coordonnées à notre liste d'exclusion. Merci.",
        "handoff": "Je vous transfère vers un conseiller humain immédiatement. Une action prioritaire vient d'être créée.",
        "voicemail": "Bonjour, ici l'assistant de Northwind Digital. N'hésitez pas à nous rappeler pour tout sujet SharePoint.",
        "closing": "Merci pour votre temps. Notre équipe assurera le suivi de votre dossier.",
        "fallback": "De quelle prestation SharePoint ou Microsoft 365 avez-vous besoin, et sous quelle échéance ?",
        "no_answer": "Pas de réponse. Tâche de rappel programmée.",
        "connected": "Appel établi. Poursuite de la qualification.",
    },
    "de": {
        "disclosure": "Guten Tag, ich bin der KI-Vertriebsassistent von Northwind Digital. Ich melde mich bezüglich Ihrer digitalen Arbeitsplatz-Initiativen.",
        "greeting": "Darf ich fragen, wie Ihr Team SharePoint derzeit im Unternehmen nutzt?",
        "qualify": "Welche Ziele verfolgen Sie mit SharePoint oder Microsoft 365 und welcher Zeitplan ist vorgesehen?",
        "faq_services": "Wir bieten SharePoint-Implementierung, Migration, Microsoft 365-Beratung und Dokumentenmanagement auf Unternehmensebene an.",
        "faq_price": "Preise werden individuell nach Projektumfang kalkuliert. Gerne vereinbare ich einen Beratungstermin mit einem Experten.",
        "internal_it": "Das ist sehr üblich. Northwind Digital arbeitet häufig partnerschaftlich mit internen IT-Teams zusammen. Wäre ein Co-Delivery-Modell interessant?",
        "interested": "Vielen Dank! Ich habe Ihr konkretes Interesse erfasst. Ein Spezialist wird sich zur Terminabsprache bei Ihnen melden.",
        "callback": "Ich plane gerne einen Rückruf durch einen Vertriebsmitarbeiter ein. Welcher Zeitpunkt passt Ihnen am besten?",
        "not_interested": "Verstanden. Wir beenden die Kontaktaufnahme und setzen Ihre Rufnummer auf unsere Sperrliste. Vielen Dank.",
        "handoff": "Ich leite Sie direkt an einen menschlichen Spezialisten weiter. Eine Prioritätsaufgabe wurde angelegt.",
        "voicemail": "Guten Tag, hier ist der digitale Assistent von Northwind Digital. Bitte rufen Sie uns bezüglich SharePoint-Services zurück.",
        "closing": "Vielen Dank für Ihre Zeit. Ein Kollege wird die nächsten Schritte für Sie koordinieren.",
        "fallback": "Welche Unterstützung bei SharePoint oder Microsoft 365 benötigen Sie und welcher Zeitrahmen ist geplant?",
        "no_answer": "Keine Antwort. Wiedervorlage erstellt.",
        "connected": "Verbindung hergestellt. Starte Qualifizierung.",
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
