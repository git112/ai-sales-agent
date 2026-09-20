from __future__ import annotations

import csv
from io import BytesIO, StringIO

from openpyxl import Workbook

EXPORT_FIELDS = [
    ("id", "Lead ID"),
    ("company", "Company"),
    ("name", "Contact"),
    ("email", "Email"),
    ("phone", "Phone"),
    ("industry", "Industry"),
    ("location", "Location"),
    ("company_size", "Company Size"),
    ("technology", "Technology"),
    ("source", "Source"),
    ("source_url", "Original URL"),
    ("opportunity_score", "Opportunity Score"),
    ("intent_level", "Intent"),
    ("qualification_status", "Qualification"),
    ("pipeline_stage", "Pipeline Stage"),
    ("campaign", "Campaign"),
    ("created_at", "Created Date"),
]


def flatten_lead(lead: dict, company: dict | None) -> dict:
    return {
        "id": lead.get("id"),
        "company": lead.get("company"),
        "name": lead.get("name") or "Not detected",
        "email": lead.get("email") or "Not detected",
        "phone": lead.get("phone") or "Not detected",
        "industry": lead.get("industry") or "Not detected",
        "location": lead.get("location") or "Not detected",
        "company_size": (company or {}).get("company_size") or lead.get("company_size") or "Not detected",
        "technology": ", ".join((company or {}).get("technologies") or lead.get("technologies") or []) or "Not detected",
        "source": lead.get("source") or "Not detected",
        "source_url": lead.get("website") or "Not detected",
        "opportunity_score": lead.get("opportunity_score") if lead.get("opportunity_score") is not None else "Not detected",
        "intent_level": lead.get("intent_level") or "Not detected",
        "qualification_status": lead.get("qualification_status") or "Not detected",
        "pipeline_stage": lead.get("pipeline_stage") or "Not detected",
        "campaign": ",".join(lead.get("campaign_ids") or []) or "Not detected",
        "created_at": lead.get("created_at") or "Not detected",
    }


def to_csv(rows: list[dict]) -> bytes:
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow([label for _, label in EXPORT_FIELDS])
    for row in rows:
        writer.writerow([row.get(key) for key, _ in EXPORT_FIELDS])
    return buf.getvalue().encode("utf-8-sig")


def to_xlsx(rows: list[dict]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"
    ws.append([label for _, label in EXPORT_FIELDS])
    for row in rows:
        ws.append([row.get(key) for key, _ in EXPORT_FIELDS])
    out = BytesIO()
    wb.save(out)
    return out.getvalue()
