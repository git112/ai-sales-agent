"""Live telephony adapter for Lumina.

Replaces the old Twilio stub. Wraps the Bolna REST client so the rest
of the app stays framework-agnostic. Demo provider continues to work
unchanged; live mode is opt-in per workspace via `workspaces.mode`.
"""
from __future__ import annotations

import logging
from typing import Any

from app import bolna

log = logging.getLogger("lumina.live_voice")


class LiveVoiceProvider:
    label = "Live voice (Bolna)"

    def reply(self, agent, user_text, history, locale="en"):  # pragma: no cover - not used
        raise RuntimeError(
            "LiveVoiceProvider.reply is unused: live conversations run on Bolna's side. "
            "The Lumina backend only dispatches + reconciles."
        )

    # ---------- agent sync ----------

    def sync_agent(self, agent: dict) -> str | None:
        if not bolna.is_configured():
            log.info("Bolna not configured — skipping sync for agent %s", agent.get("id"))
            return None
        existing = agent.get("bolna_agent_id")
        try:
            if existing:
                bolna.patch_agent(existing, agent)
                return existing
            return bolna.create_agent(agent)
        except bolna.BolnaError as e:
            log.exception("Bolna sync failed for agent %s: %s", agent.get("id"), e)
            raise

    def delete_agent(self, agent: dict) -> None:
        bid = agent.get("bolna_agent_id")
        if not bid or not bolna.is_configured():
            return
        try:
            bolna.delete_agent(bid)
        except bolna.BolnaError as e:
            log.warning("Bolna delete failed for agent %s (%s): %s", agent.get("id"), bid, e)

    # ---------- outbound dispatch ----------

    def dispatch(
        self,
        *,
        agent: dict,
        recipient_phone: str,
        lead: dict | None,
        from_phone: str | None,
        language: str | None,
        extra_user_data: dict | None = None,
        scheduled_at: str | None = None,
    ) -> dict:
        if not agent.get("bolna_agent_id"):
            raise RuntimeError(f"Agent {agent.get('id')} has no bolna_agent_id; sync it first.")
        if not recipient_phone:
            raise RuntimeError("Recipient phone number is required for live dispatch.")
        active_lang = bolna._active_language(language, lead)
        user_data = {
            "prospect_name": (lead or {}).get("name") or "there",
            "company_name": (lead or {}).get("company") or agent.get("company_name") or "Lumina",
            "language": active_lang,
            "lead_id": (lead or {}).get("id") or "",
            "call_objective": agent.get("call_objective") or "",
        }
        if extra_user_data:
            user_data.update(extra_user_data)
        return bolna.dispatch_call(
            bolna_agent_id=agent["bolna_agent_id"],
            recipient=recipient_phone,
            from_phone=from_phone or None,
            user_data=user_data,
            scheduled_at=scheduled_at,
        )

    # ---------- introspection ----------

    def health(self) -> dict[str, Any]:
        if not bolna.is_configured():
            return {"configured": False}
        try:
            me = bolna.user_me()
            return {"configured": True, "user": me}
        except bolna.BolnaError as e:
            return {"configured": True, "error": str(e)}


live_voice = LiveVoiceProvider()
