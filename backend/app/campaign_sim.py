from __future__ import annotations

from datetime import datetime, timezone

DEFAULT_SEQUENCE = ["No Answer", "Voicemail", "Interested"]


def parse_hhmm(value: str) -> int | None:
    try:
        h, m = value.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return None


def in_quiet_hours(now: datetime, quiet: dict | None) -> bool:
    if not quiet:
        return False
    start = parse_hhmm(str(quiet.get("start") or ""))
    end = parse_hhmm(str(quiet.get("end") or ""))
    if start is None or end is None:
        return False
    minutes = now.hour * 60 + now.minute
    if start == end:
        return False
    if start < end:
        return start <= minutes < end
    return minutes >= start or minutes < end


def next_step_plan(campaign: dict, lead_id: str, now: datetime | None = None, force: bool = False) -> dict:
    now = now or datetime.now(timezone.utc)
    policy = campaign.get("retry_policy") or {}
    sequence = policy.get("sequence") or DEFAULT_SEQUENCE
    max_attempts = int(policy.get("max_attempts") or len(sequence))
    attempts = (campaign.get("lead_attempts") or {}).get(lead_id) or {"count": 0, "timeline": []}
    count = int(attempts.get("count") or 0)
    quiet = campaign.get("quiet_hours")
    if campaign.get("status") == "paused":
        return {"eligible": False, "reason": "Campaign paused", "attempt": count, "label": "DEMO CAMPAIGN SIMULATION"}
    if campaign.get("status") not in ("running", "scheduled", "draft"):
        return {"eligible": False, "reason": f"Campaign status is {campaign.get('status')}", "attempt": count, "label": "DEMO CAMPAIGN SIMULATION"}
    if not force and in_quiet_hours(now, quiet):
        return {
            "eligible": False,
            "reason": "Quiet hours",
            "attempt": count,
            "retry_eligible": True,
            "label": "DEMO CAMPAIGN SIMULATION",
        }
    if count >= max_attempts or count >= len(sequence):
        return {
            "eligible": False,
            "reason": "Maximum attempts reached",
            "attempt": count,
            "retry_eligible": False,
            "final": True,
            "label": "DEMO CAMPAIGN SIMULATION",
        }
    outcome = sequence[count]
    retry_after = count + 1 < min(max_attempts, len(sequence))
    return {
        "eligible": True,
        "attempt": count + 1,
        "next_attempt": count + 2 if retry_after else None,
        "planned_outcome": outcome,
        "retry_eligible": retry_after and outcome in ("No Answer", "Voicemail"),
        "label": "DEMO CAMPAIGN SIMULATION",
    }
