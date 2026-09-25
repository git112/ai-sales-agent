"""Bolna REST client + prompt/translation glue for Lumina.

Encapsulates every call to https://api.bolna.ai so the rest of the app
talks to one module. Prompt construction is intentionally kept inside
this file because Bolna's multilingual_config shape (per-language
synthesizer/transcriber/system_prompt) is specific to the platform.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Iterable

import httpx

from app.core.config import settings

log = logging.getLogger("lumina.bolna")

BASE_URL = settings.bolna_base_url.rstrip("/")

LANGS = ("en", "hi", "gu", "es", "fr", "de")

WELCOME_LOCALES = {
    "en": "Hello {prospect_name}, this is an AI assistant calling on behalf of {company_name}.",
    "hi": "नमस्ते {prospect_name}, मैं {company_name} की ओर से AI सहायक बोल रही हूँ।",
    "gu": "નમસ્તે {prospect_name}, હું {company_name} તરફથી AI સહાયક બોલું છું.",
    "es": "Hola {prospect_name}, le habla el asistente de IA de {company_name}.",
    "fr": "Bonjour {prospect_name}, je suis l'assistant IA de {company_name}.",
    "de": "Hallo {prospect_name}, ich bin der KI-Assistent von {company_name}.",
}

SYNTHESIZER_LOCALES = {
    "en": {"provider": "cartesia", "model": "sonic-3", "voice": "Devansh", "voice_id": "1259b7e3-cb8a-43df-9446-30971a46b8b0", "buffer_size": 40},
    "hi": {"provider": "cartesia", "model": "sonic-3", "voice": "Arushi", "voice_id": "95d51f79-c397-46f9-b49a-23763d3eaa2d", "buffer_size": 40},
    "gu": {"provider": "cartesia", "model": "sonic-3", "voice": "Isha", "voice_id": "4590a461-bc68-4a50-8d14-ac04f5923d22", "buffer_size": 40},
    "es": {"provider": "cartesia", "model": "sonic-3", "voice": "Devansh", "voice_id": "1259b7e3-cb8a-43df-9446-30971a46b8b0", "buffer_size": 40},
    "fr": {"provider": "cartesia", "model": "sonic-3", "voice": "Devansh", "voice_id": "1259b7e3-cb8a-43df-9446-30971a46b8b0", "buffer_size": 40},
    "de": {"provider": "cartesia", "model": "sonic-3", "voice": "Devansh", "voice_id": "1259b7e3-cb8a-43df-9446-30971a46b8b0", "buffer_size": 40},
}

TRANSCRIBER_LOCALES = {
    "en": {"provider": "deepgram", "model": "nova-3", "language": "en"},
    "hi": {"provider": "deepgram", "model": "nova-3", "language": "hi"},
    "gu": {"provider": "deepgram", "model": "nova-3", "language": "gu"},
    "es": {"provider": "deepgram", "model": "nova-3", "language": "es"},
    "fr": {"provider": "deepgram", "model": "nova-3", "language": "fr"},
    "de": {"provider": "deepgram", "model": "nova-3", "language": "de"},
}


class BolnaError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def is_configured() -> bool:
    return bool(settings.bolna_api_key)


def _headers() -> dict[str, str]:
    if not settings.bolna_api_key:
        raise BolnaError("BOLNA_API_KEY is not configured")
    return {
        "Authorization": f"Bearer {settings.bolna_api_key}",
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, *, params: dict | None = None, json: dict | None = None, timeout: float = 30.0) -> Any:
    url = f"{BASE_URL}{path}"
    try:
        r = httpx.request(method, url, headers=_headers(), params=params, json=json, timeout=timeout)
    except httpx.HTTPError as e:
        raise BolnaError(f"Bolna transport error: {e}") from e
    if r.status_code >= 400:
        raise BolnaError(f"Bolna {method} {path} -> {r.status_code}: {r.text[:500]}", status_code=r.status_code, payload=r.text)
    if not r.content:
        return None
    try:
        return r.json()
    except Exception:
        return r.text


# ---------------- prompt synthesis ----------------

def _sanitize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _system_prompt_for(lang: str, agent: dict) -> str:
    from app.voice import scripts

    s = scripts(lang)
    objective = _sanitize(agent.get("call_objective") or "")
    guardrails = agent.get("guardrails") or []
    guardrail_block = ""
    if guardrails:
        guardrail_block = "Guardrails: " + "; ".join(str(g) for g in guardrails) + "."
    base = (
        f"You are a polite, concise AI voice agent calling on behalf of {_sanitize(agent.get('company_name') or 'our company')}. "
        "Always disclose that you are an AI assistant at the start of the call. "
        "Reply in the language the caller is using. Keep responses to one or two short sentences. "
        f"Goal: {objective or 'qualify interest and capture requirements for a follow-up by a human specialist.'} "
        f"Greeting: {s['greeting']} Qualification: {s['qualify']} "
        f"Services you offer (only approved knowledge): {s['faq_services']} "
        f"Internal IT handoff: {s['internal_it']} "
        f"If the prospect is interested, respond with: {s['interested']} {s['closing']} "
        f"If they want a callback: {s['callback']} "
        f"If they ask for a human: {s['handoff']} "
        f"If they are not interested or ask to opt out: {s['not_interested']} "
        "Never invent pricing, contacts, or commitments. If asked something you cannot answer from approved knowledge, "
        "offer a callback from a human specialist. "
        f"{guardrail_block}"
    )
    return base


def _active_language(language: str | None, lead: dict | None) -> str:
    lang = (language or "").lower().strip()
    if lang and lang != "auto" and lang in LANGS:
        return lang
    loc = ((lead or {}).get("location") or "").lower()
    if any(w in loc for w in ["gujarat", "ahmedabad", "surat", "vadodara", "rajkot"]):
        return "gu"
    if any(w in loc for w in ["india", "delhi", "mumbai", "bangalore", "noida", "gurgaon", "hyderabad", "pune"]):
        return "hi"
    if any(w in loc for w in ["spain", "mexico", "madrid", "barcelona", "argentina", "colombia"]):
        return "es"
    if any(w in loc for w in ["france", "paris", "lyon", "quebec", "belgium"]):
        return "fr"
    if any(w in loc for w in ["germany", "berlin", "munich", "austria", "switzerland", "frankfurt"]):
        return "de"
    return "en"


def build_agent_payload(agent: dict) -> dict:
    company = agent.get("company_name") or "Lumina"
    name = agent.get("name") or f"{company} Agent"
    welcome_en = WELCOME_LOCALES["en"].format(prospect_name="{prospect_name}", company_name=company)

    languages = {}
    for lang in LANGS:
        synth = SYNTHESIZER_LOCALES[lang]
        tr = TRANSCRIBER_LOCALES[lang]
        s = (synth, dict(synth))  # not used; placeholder to satisfy type checker in dev
        languages[lang] = {
            "agent_name": name,
            "system_prompt": _system_prompt_for(lang, agent),
            "synthesizer": {
                "provider": synth["provider"],
                "stream": True,
                "buffer_size": synth["buffer_size"],
                "audio_format": "wav",
                "provider_config": {
                    "model": synth["model"],
                    "voice": synth["voice"],
                    "voice_id": synth["voice_id"],
                    "language": lang,
                },
            },
            "transcriber": {
                "provider": tr["provider"],
                "model": tr["model"],
                "language": tr["language"],
                "stream": True,
                "encoding": "linear16",
                "sampling_rate": 16000,
                "endpointing": 700,
            },
            "handoff_message": (
                "One moment, connecting you with a specialist who speaks {language}."
                if lang == "en"
                else f"Un momento, le conecto con un especialista que habla {{language}}."
                if lang == "es"
                else f"Ein Moment, ich verbinde Sie mit einem Spezialisten, der {{language}} spricht."
                if lang == "de"
                else f"Un instant, je vous mets en relation avec un conseiller qui parle {{language}}."
                if lang == "fr"
                else "એક મિનિટ, હું તમને {language} બોલતા નિષ્ણાત સાથે જોડું છું."
                if lang == "gu"
                else "एक मिनट, मैं आपको {language} बोलने वाले विशेषज्ञ से जोड़ रही हूँ।"
            ),
        }

    payload = {
        "agent_config": {
            "agent_name": name,
            "agent_welcome_message": welcome_en,
            "agent_type": settings.bolna_default_agent_type or "other",
            "webhook_url": settings.bolna_webhook_url or None,
            "calling_guardrails": {
                "call_start_hour": int((agent.get("guardrail_hours") or {}).get("start", 9)),
                "call_end_hour": int((agent.get("guardrail_hours") or {}).get("end", 18)),
            },
            "tasks": [
                {
                    "task_type": "conversation",
                    "tools_config": {
                        "llm_agent": {
                            "agent_type": "simple_llm_agent",
                            "agent_flow_type": "streaming",
                            "llm_config": {
                                "provider": "openai",
                                "family": "openai",
                                "model": "gpt-4.1-mini",
                                "max_tokens": 200,
                                "temperature": 0.2,
                            },
                        },
                        "synthesizer": {
                            "provider": SYNTHESIZER_LOCALES["en"]["provider"],
                            "stream": True,
                            "buffer_size": SYNTHESIZER_LOCALES["en"]["buffer_size"],
                            "audio_format": "wav",
                            "provider_config": {
                                "model": SYNTHESIZER_LOCALES["en"]["model"],
                                "voice": SYNTHESIZER_LOCALES["en"]["voice"],
                                "voice_id": SYNTHESIZER_LOCALES["en"]["voice_id"],
                                "language": "en",
                            },
                        },
                        "transcriber": {
                            "provider": TRANSCRIBER_LOCALES["en"]["provider"],
                            "model": TRANSCRIBER_LOCALES["en"]["model"],
                            "language": TRANSCRIBER_LOCALES["en"]["language"],
                            "stream": True,
                            "encoding": "linear16",
                            "sampling_rate": 16000,
                            "endpointing": 700,
                        },
                        "input": {"provider": "plivo", "format": "wav"},
                        "output": {"provider": "plivo", "format": "wav"},
                        "multilingual_config": {
                            "enabled": True,
                            "active_language": "en",
                            "switch_tool_description": (
                                "Respond in the language the caller is currently speaking. "
                                "Default to English when the caller's language is unclear."
                            ),
                            "languages": languages,
                        },
                    },
                    "toolchain": {
                        "execution": "parallel",
                        "pipelines": [["transcriber", "llm", "synthesizer"]],
                    },
                    "task_config": {
                        "call_cancellation_prompt": "Sorry, the call is being disconnected.",
                        "call_terminate": 600,
                        "hangup_after_silence": 12,
                        "incremental_delay": 100,
                        "number_of_words_for_interruption": 2,
                        "backchanneling": False,
                        "call_hangup_message": {
                            "en": "Thank you for your time. Goodbye.",
                            "hi": "आपके समय के लिए धन्यवाद। अलविदा।",
                            "gu": "તમારા સમય બદલ આભાર. આવજો.",
                            "es": "Gracias por su tiempo. Adiós.",
                            "fr": "Merci pour votre temps. Au revoir.",
                            "de": "Vielen Dank für Ihre Zeit. Auf Wiedersehen.",
                        },
                        "check_user_online_message": {
                            "en": "Hello, are you there?",
                            "hi": "नमस्ते, क्या आप सुन रहे हैं?",
                            "gu": "નમસ્તે, શું તમે સાંભળી રહ્યા છો?",
                            "es": "Hola, ¿sigue ahí?",
                            "fr": "Bonjour, êtes-vous toujours là ?",
                            "de": "Hallo, sind Sie noch dran?",
                        },
                    },
                }
            ],
        },
        "agent_prompts": {
            "task_1": {"system_prompt": _system_prompt_for("en", agent)},
        },
    }
    return payload


def patch_payload_for(agent: dict) -> dict:
    full = build_agent_payload(agent)
    return {
        "agent_config": {
            "agent_name": full["agent_config"]["agent_name"],
            "agent_welcome_message": full["agent_config"]["agent_welcome_message"],
            "webhook_url": full["agent_config"]["webhook_url"],
            "calling_guardrails": full["agent_config"]["calling_guardrails"],
        },
        "agent_prompts": full["agent_prompts"],
    }


# ---------------- Bolna REST wrappers ----------------

def create_agent(agent: dict) -> str:
    payload = build_agent_payload(agent)
    resp = _request("POST", "/v2/agent", json=payload)
    if not isinstance(resp, dict):
        raise BolnaError(f"Unexpected Bolna create_agent response: {resp!r}")
    agent_id = resp.get("agent_id") or (resp.get("data") or {}).get("agent_id")
    if not agent_id:
        raise BolnaError(f"Bolna create_agent returned no agent_id: {resp!r}")
    return agent_id


def patch_agent(bolna_agent_id: str, agent: dict) -> dict:
    return _request("PATCH", f"/v2/agent/{bolna_agent_id}", json=patch_payload_for(agent))


def delete_agent(bolna_agent_id: str) -> dict:
    return _request("DELETE", f"/v2/agent/{bolna_agent_id}")


def dispatch_call(
    *,
    bolna_agent_id: str,
    recipient: str,
    from_phone: str | None,
    user_data: dict,
    scheduled_at: str | None = None,
) -> dict:
    body: dict[str, Any] = {
        "agent_id": bolna_agent_id,
        "recipient_phone_number": recipient,
        "user_data": user_data,
    }
    if from_phone:
        body["from_phone_number"] = from_phone
    if scheduled_at:
        body["scheduled_at"] = scheduled_at
    return _request("POST", "/call", json=body)


def get_execution(execution_id: str) -> dict:
    return _request("GET", f"/executions/{execution_id}")


def stop_execution(execution_id: str) -> dict:
    return _request("POST", f"/call/{execution_id}/stop")


def user_me() -> dict:
    return _request("GET", "/user/me")


def list_phone_numbers() -> list[dict]:
    resp = _request("GET", "/phone-numbers/all")
    if isinstance(resp, list):
        return resp
    if isinstance(resp, dict) and isinstance(resp.get("data"), list):
        return resp["data"]
    return []


# ---------------- outcome mapping ----------------

TERMINAL_STATUSES = {
    "completed",
    "no-answer",
    "busy",
    "failed",
    "canceled",
    "stopped",
    "error",
    "balance-low",
}


STATUS_TO_OUTCOME = {
    "completed": "Connected",
    "no-answer": "No Answer",
    "busy": "No Answer",
    "failed": "Failed",
    "canceled": "Failed",
    "stopped": "Failed",
    "error": "Failed",
    "balance-low": "Failed",
    "call-disconnected": "Connected",
    "voicemail": "Voicemail",
}


def extract_outcome(payload: dict) -> str:
    status = (payload.get("status") or "").lower()
    if payload.get("answered_by_voice_mail"):
        return "Voicemail"
    return STATUS_TO_OUTCOME.get(status, "Connected" if status == "in-progress" else "Unknown")


def extract_transcript_turns(payload: dict) -> list[dict]:
    raw = payload.get("transcript")
    turns: list[dict] = []
    AGENT_ROLES = {"assistant", "agent", "ai", "bot"}

    def _speaker(role: str) -> str:
        return "agent" if (role or "").lower() in AGENT_ROLES else "prospect"

    def _strip_prefix(text: str) -> tuple[str, str | None]:
        """Bolna sometimes prefixes text with 'assistant: ' or 'user: '. Detect and strip."""
        import re
        m = re.match(r"^\s*(assistant|user|agent|prospect|ai|bot)\s*:\s*(.*)$", text, flags=re.IGNORECASE | re.DOTALL)
        if m:
            prefix = m.group(1).lower()
            return m.group(2).strip(), ("agent" if prefix in AGENT_ROLES else "prospect")
        return text.strip(), None

    if isinstance(raw, list):
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            role = entry.get("role") or entry.get("speaker") or "agent"
            text = entry.get("content") or entry.get("text") or entry.get("message") or ""
            if not text:
                continue
            cleaned, prefix_speaker = _strip_prefix(text)
            if not cleaned:
                continue
            speaker = prefix_speaker or _speaker(role)
            ts = entry.get("timestamp") or entry.get("ts") or entry.get("time")
            turns.append({"speaker": speaker, "text": cleaned, **({"ts": ts} if ts else {})})
    elif isinstance(raw, str) and raw.strip():
        cleaned, prefix_speaker = _strip_prefix(raw)
        if cleaned:
            turns.append({"speaker": prefix_speaker or "agent", "text": cleaned})
    elif isinstance(payload.get("conversation"), list):
        for entry in payload["conversation"]:
            if not isinstance(entry, dict):
                continue
            role = entry.get("role") or entry.get("speaker") or "agent"
            text = entry.get("message") or entry.get("content") or entry.get("text") or ""
            if not text:
                continue
            cleaned, prefix_speaker = _strip_prefix(text)
            if not cleaned:
                continue
            turns.append({"speaker": prefix_speaker or _speaker(role), "text": cleaned})
    return turns
