from __future__ import annotations

from typing import Any

from app.store import get_by_id


OPS = {"equals", "contains", "greater_than", "less_than", "in"}

FIELD_GETTERS = {
    "industry": lambda l, _: l.get("industry"),
    "location": lambda l, _: l.get("location"),
    "company_size": lambda l, c: (c or {}).get("company_size") or l.get("company_size"),
    "technology": lambda l, c: " ".join((c or {}).get("technologies") or l.get("technologies") or []),
    "opportunity_score": lambda l, _: l.get("opportunity_score"),
    "intent_level": lambda l, _: l.get("intent_level"),
    "lead_source": lambda l, _: l.get("source"),
    "campaign": lambda l, _: " ".join(l.get("campaign_ids") or []),
    "qualification_status": lambda l, _: l.get("qualification_status"),
    "pipeline_stage": lambda l, _: l.get("pipeline_stage"),
}


def _op(op: str, actual: Any, expected: Any) -> bool:
    if actual is None and expected not in (None, ""):
        return False
    op = (op or "equals").lower()
    if op == "equals":
        return str(actual or "").lower() == str(expected or "").lower()
    if op == "contains":
        return str(expected or "").lower() in str(actual or "").lower()
    if op == "greater_than":
        try:
            return float(actual) > float(expected)
        except (TypeError, ValueError):
            return False
    if op == "less_than":
        try:
            return float(actual) < float(expected)
        except (TypeError, ValueError):
            return False
    if op == "in":
        values = expected if isinstance(expected, list) else [x.strip() for x in str(expected).split(",")]
        return str(actual or "").lower() in {str(v).lower() for v in values}
    return False


def normalize_filters(filters: Any) -> list[dict]:
    if isinstance(filters, list):
        return [f for f in filters if isinstance(f, dict) and f.get("field")]
    if not isinstance(filters, dict):
        return []
    out = []
    mapping = {
        "industry": ("industry", "equals"),
        "location": ("location", "contains"),
        "location_contains": ("location", "contains"),
        "company_size": ("company_size", "equals"),
        "technology": ("technology", "contains"),
        "opportunity_score": ("opportunity_score", "greater_than"),
        "min_score": ("opportunity_score", "greater_than"),
        "intent_level": ("intent_level", "equals"),
        "intent": ("intent_level", "equals"),
        "lead_source": ("lead_source", "equals"),
        "source": ("lead_source", "equals"),
        "campaign": ("campaign", "contains"),
        "qualification_status": ("qualification_status", "equals"),
        "pipeline_stage": ("pipeline_stage", "equals"),
    }
    for k, v in filters.items():
        if v in (None, "", []):
            continue
        if k not in mapping:
            continue
        field, op = mapping[k]
        val = v
        if k == "min_score":
            try:
                val = float(v) - 0.0001
            except (TypeError, ValueError):
                continue
        out.append({"field": field, "op": op, "value": val})
    return out


def match_lead(lead: dict, filters: Any) -> bool:
    rules = normalize_filters(filters)
    if not rules:
        return True
    company = get_by_id("companies", lead.get("company_id") or "") if lead.get("company_id") else None
    for rule in rules:
        getter = FIELD_GETTERS.get(rule.get("field") or "")
        if not getter:
            continue
        actual = getter(lead, company)
        if not _op(rule.get("op") or "equals", actual, rule.get("value")):
            return False
    return True


def apply_segment(leads: list[dict], segment: dict) -> list[dict]:
    if segment.get("type") == "static":
        ids = set(segment.get("lead_ids") or [])
        return [l for l in leads if l.get("id") in ids]
    return [l for l in leads if match_lead(l, segment.get("filters"))]
