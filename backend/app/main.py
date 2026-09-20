from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, EmailStr

from app.ai import demo_ai
from app.core.config import settings
from app.core.security import create_token, hash_password, verify_password
from app.deps import current_user, require_admin, workspace_id
from app.knowledge import UPLOAD_ROOT, extract_text, knowledge_store
from app.sources import ADAPTERS
from app.store import (
    audit,
    by_workspace,
    create_record,
    delete_record,
    filter_records,
    get_all,
    get_by_id,
    new_id,
    read_json,
    search_records,
    update_record,
    utcnow,
    write_json,
)
from app.voice import agent_reply, detect_interest, opening_message

app = FastAPI(title="Lumina API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_rate: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        key = request.client.host if request.client else "anon"
        now = datetime.now(timezone.utc).timestamp()
        window = [t for t in _rate[key] if now - t < 60]
        if len(window) > 180:
            return JSONResponse({"error": {"code": "rate_limited", "message": "Too many requests"}}, status_code=429)
        window.append(now)
        _rate[key] = window
    return await call_next(request)


@app.exception_handler(StarletteHTTPException)
async def http_error(_, exc: StarletteHTTPException):
    return JSONResponse({"error": {"code": "http_error", "message": exc.detail}}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def valid_error(_, exc: RequestValidationError):
    return JSONResponse({"error": {"code": "validation_error", "message": "Invalid request"}}, status_code=422)


@app.exception_handler(Exception)
async def on_error(_, exc: Exception):
    return JSONResponse({"error": {"code": "server_error", "message": "Unexpected error"}}, status_code=500)


def strip_user(u: dict) -> dict:
    out = {k: v for k, v in u.items() if k != "password_hash"}
    return out


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class SignupIn(BaseModel):
    name: str
    email: EmailStr
    password: str


class ForgotIn(BaseModel):
    email: EmailStr


class OnboardingIn(BaseModel):
    company_name: str
    website: str | None = None
    description: str | None = None
    industry: str | None = None
    location: str | None = None
    products: list[str] = []
    services: list[str] = []
    technologies: list[str] = []
    target_industries: list[str] = []
    target_locations: list[str] = []
    company_size: str | None = None
    target_roles: list[str] = []
    keywords: list[str] = []


class SearchIn(BaseModel):
    query: str


class LeadIn(BaseModel):
    name: str | None = None
    company: str | None = None
    email: str | None = None
    phone: str | None = None
    job_title: str | None = None
    website: str | None = None
    location: str | None = None
    industry: str | None = None
    notes: str | None = None


class CampaignIn(BaseModel):
    name: str
    campaign_type: str
    objective: str | None = None
    agent_id: str
    lead_ids: list[str]
    qualification_questions: list[str] = []
    language: str = "en"
    schedule: str = "immediate"
    scheduled_at: str | None = None
    timezone: str = "Asia/Kolkata"
    retry_policy: dict | None = None


class AgentIn(BaseModel):
    name: str
    purpose: str | None = None
    language: str = "en"
    voice: str = "professional_female"
    tone: str = "consultative"
    knowledge_doc_ids: list[str] = []
    call_objective: str | None = None
    qualification_questions: list[str] = []


class PlaygroundIn(BaseModel):
    message: str
    history: list[dict] = []
    language: str = "en"


class CopilotIn(BaseModel):
    question: str


class SavedSearchIn(BaseModel):
    name: str
    query: str
    filters: dict = {}
    source: str = "Demo Source"
    frequency: str = "daily"
    status: str = "active"


class SegmentIn(BaseModel):
    name: str
    type: str = "dynamic"
    filters: dict = {}
    lead_ids: list[str] = []


class TaskPatch(BaseModel):
    status: str | None = None
    assignee: str | None = None
    due: str | None = None
    title: str | None = None


@app.get("/health")
def health():
    return {"ok": True, "mode": settings.default_app_mode}


@app.post("/api/v1/auth/signup")
def signup(body: SignupIn):
    if any(u.get("email") == body.email.lower() for u in get_all("users")):
        raise HTTPException(400, "Email already registered")
    user = create_record(
        "users",
        {
            "id": new_id("user"),
            "name": body.name,
            "email": body.email.lower(),
            "password_hash": hash_password(body.password),
            "role": "user",
            "locale": "en",
            "workspace_id": None,
            "created_at": utcnow(),
        },
    )
    ws = create_record(
        "workspaces",
        {
            "id": new_id("workspace"),
            "name": f"{body.name}'s workspace",
            "owner_user_id": user["id"],
            "mode": "demo",
            "onboarding_complete": False,
            "created_at": utcnow(),
        },
    )
    update_record("users", user["id"], {"workspace_id": ws["id"]})
    user["workspace_id"] = ws["id"]
    token = create_token({"sub": user["id"], "role": user["role"], "workspace_id": ws["id"]})
    audit(ws["id"], user["id"], "signup", "user", user["id"])
    return {"token": token, "user": strip_user(user), "workspace": ws}


@app.post("/api/v1/auth/login")
def login(body: LoginIn):
    user = next((u for u in get_all("users") if u.get("email") == body.email.lower()), None)
    if not user or not verify_password(body.password, user.get("password_hash") or ""):
        raise HTTPException(401, "Invalid email or password")
    token = create_token({"sub": user["id"], "role": user["role"], "workspace_id": user.get("workspace_id")})
    audit(user.get("workspace_id"), user["id"], "login", "user", user["id"])
    return {"token": token, "user": strip_user(user)}


@app.post("/api/v1/auth/logout")
def logout(user=Depends(current_user)):
    audit(user.get("workspace_id"), user["id"], "logout", "user", user["id"])
    return {"ok": True}


@app.post("/api/v1/auth/forgot-password")
def forgot(body: ForgotIn):
    return {"ok": True, "message": "If the account exists, a reset link would be emailed. Demo MVP does not send email."}


@app.get("/api/v1/auth/me")
def me(user=Depends(current_user)):
    return strip_user(user)


@app.get("/api/v1/workspaces")
def list_workspaces(user=Depends(current_user)):
    if user.get("role") == "admin":
        return get_all("workspaces")
    return [w for w in get_all("workspaces") if w.get("owner_user_id") == user["id"] or w.get("id") == user.get("workspace_id")]


@app.post("/api/v1/workspaces")
def create_ws(name: str = Form(...), user=Depends(current_user)):
    ws = create_record(
        "workspaces",
        {
            "id": new_id("workspace"),
            "name": name,
            "owner_user_id": user["id"],
            "mode": "demo",
            "onboarding_complete": False,
            "created_at": utcnow(),
        },
    )
    update_record("users", user["id"], {"workspace_id": ws["id"]})
    return ws


@app.post("/api/v1/workspaces/{wid}/select")
def select_ws(wid: str, user=Depends(current_user)):
    ws = get_by_id("workspaces", wid)
    if not ws:
        raise HTTPException(404, "Workspace not found")
    if user.get("role") != "admin" and ws.get("owner_user_id") != user["id"] and wid != user.get("workspace_id"):
        raise HTTPException(403, "Forbidden")
    update_record("users", user["id"], {"workspace_id": wid})
    token = create_token({"sub": user["id"], "role": user["role"], "workspace_id": wid})
    return {"token": token, "workspace": ws}


@app.get("/api/v1/workspaces/{wid}/mode")
def get_mode(wid: str, user=Depends(current_user)):
    ws = get_by_id("workspaces", wid)
    if not ws:
        raise HTTPException(404, "Workspace not found")
    if user.get("role") != "admin" and ws.get("owner_user_id") != user["id"] and wid != user.get("workspace_id"):
        raise HTTPException(403, "Forbidden")
    return {"mode": ws.get("mode"), "is_demo": ws.get("mode") == "demo"}


@app.patch("/api/v1/workspaces/{wid}/mode")
def set_mode(wid: str, mode: str = Form(...), user=Depends(current_user)):
    if mode not in ("demo", "live"):
        raise HTTPException(400, "mode must be demo or live")
    ws = update_record("workspaces", wid, {"mode": mode})
    if not ws:
        raise HTTPException(404, "Workspace not found")
    audit(wid, user["id"], "set_mode", "workspace", wid, {"mode": mode})
    return ws


@app.get("/api/v1/business-profile")
def get_profile(wid: str = Depends(workspace_id)):
    rows = by_workspace("business_profiles", wid)
    return rows[0] if rows else None


@app.patch("/api/v1/business-profile")
def patch_profile(payload: dict, wid: str = Depends(workspace_id), user=Depends(current_user)):
    rows = by_workspace("business_profiles", wid)
    if not rows:
        raise HTTPException(404, "No profile")
    patch = {k: v for k, v in payload.items() if k != "id"}
    patch["last_updated"] = utcnow()
    rec = update_record("business_profiles", rows[0]["id"], patch)
    audit(wid, user["id"], "patch_profile", "business_profile", rec["id"])
    return rec


@app.post("/api/v1/business-profile/analyze")
def analyze_profile(body: OnboardingIn, wid: str = Depends(workspace_id), user=Depends(current_user)):
    docs = by_workspace("knowledge_documents", wid)
    text = "\n".join(d.get("extracted_text") or "" for d in docs)
    understood = demo_ai.understand_business({**body.model_dump(), "documents_text": text, "company_name": body.company_name})
    existing = by_workspace("business_profiles", wid)
    record = {
        "workspace_id": wid,
        "approved": False,
        "is_demo": True,
        "company_name": body.company_name,
        "website": body.website,
        "industry": body.industry,
        "location": body.location,
        "description": body.description,
        **understood,
        "source": "Onboarding form + knowledge documents",
        "confidence": 0.8,
        "last_updated": utcnow(),
    }
    if existing:
        record = update_record("business_profiles", existing[0]["id"], record) or {**existing[0], **record}
    else:
        record = create_record("business_profiles", {**record, "id": new_id("profile")})
    audit(wid, user["id"], "analyze_business", "business_profile", record["id"])
    return record


@app.post("/api/v1/onboarding")
def onboarding(body: OnboardingIn, wid: str = Depends(workspace_id), user=Depends(current_user)):
    profile = analyze_profile(body, wid, user)
    update_record("workspaces", wid, {"onboarding_complete": False})
    return {"profile": profile, "message": "Here's what AI understood about your business."}


@app.post("/api/v1/business-profile/approve")
def approve_profile(payload: dict, wid: str = Depends(workspace_id), user=Depends(current_user)):
    rows = by_workspace("business_profiles", wid)
    if not rows:
        raise HTTPException(404, "No profile")
    patch = {k: v for k, v in payload.items() if k != "id"}
    patch["approved"] = True
    patch["last_updated"] = utcnow()
    rec = update_record("business_profiles", rows[0]["id"], patch)
    update_record("workspaces", wid, {"onboarding_complete": True})
    audit(wid, user["id"], "approve_profile", "business_profile", rec["id"])
    return rec


@app.get("/api/v1/knowledge")
def list_knowledge(wid: str = Depends(workspace_id)):
    return by_workspace("knowledge_documents", wid)


@app.get("/api/v1/knowledge/search")
def search_knowledge(q: str, wid: str = Depends(workspace_id)):
    return {"query": q, "chunks": knowledge_store.search(wid, q)}


@app.post("/api/v1/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...), wid: str = Depends(workspace_id), user=Depends(current_user)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".pdf", ".docx", ".txt"):
        raise HTTPException(400, "Only PDF, DOCX, TXT allowed")
    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(400, "File too large")
    dest_dir = UPLOAD_ROOT / wid
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / (file.filename or "upload.txt")
    dest.write_bytes(content)
    doc = create_record(
        "knowledge_documents",
        {
            "id": new_id("doc"),
            "workspace_id": wid,
            "filename": file.filename,
            "type": suffix.lstrip("."),
            "status": "processing",
            "size_bytes": len(content),
            "chunk_count": 0,
            "is_demo": True,
            "uploaded_at": utcnow(),
            "last_updated": utcnow(),
            "extracted_text": "",
        },
    )
    try:
        text = extract_text(dest, suffix)
        knowledge_store.index_document(doc, text)
        doc = get_by_id("knowledge_documents", doc["id"])
    except Exception:
        update_record("knowledge_documents", doc["id"], {"status": "failed"})
        raise HTTPException(400, "Could not process file")
    audit(wid, user["id"], "upload_knowledge", "knowledge_document", doc["id"])
    return doc


@app.delete("/api/v1/knowledge/{doc_id}")
def delete_knowledge(doc_id: str, wid: str = Depends(workspace_id), user=Depends(current_user)):
    doc = get_by_id("knowledge_documents", doc_id)
    if not doc or doc.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    delete_record("knowledge_documents", doc_id)
    audit(wid, user["id"], "delete_knowledge", "knowledge_document", doc_id)
    return {"ok": True}


@app.post("/api/v1/opportunities/search")
def search_opps(body: SearchIn, wid: str = Depends(workspace_id), user=Depends(current_user)):
    criteria = demo_ai.plan_search(body.query)
    results = []
    for adapter in ADAPTERS:
        if adapter.is_demo:
            results.extend(adapter.search(wid, criteria))
    seen = set()
    unique = []
    for r in results:
        key = r.get("id") or r.get("title")
        if key in seen:
            continue
        seen.add(key)
        unique.append({**r, "label": "DEMO DATA", "source": r.get("source") or "Demo Source", "company_name": r.get("company") or (get_by_id("companies", r.get("company_id") or "") or {}).get("name")})
    audit(wid, user["id"], "search_opportunities", "opportunity", None, {"query": body.query})
    return {"criteria": criteria, "source_note": "Demo Source — not live discovery", "results": unique}


@app.get("/api/v1/opportunities")
def list_opps(wid: str = Depends(workspace_id)):
    rows = by_workspace("opportunities", wid)
    out = []
    for o in rows:
        c = get_by_id("companies", o.get("company_id") or "")
        out.append({**o, "company_name": (c or {}).get("name")})
    return out


@app.get("/api/v1/opportunities/{oid}")
def get_opp(oid: str, wid: str = Depends(workspace_id)):
    o = get_by_id("opportunities", oid)
    if not o or o.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    company = get_by_id("companies", o.get("company_id") or "")
    contact = get_by_id("contacts", o.get("contact_id") or "") if o.get("contact_id") else None
    signals = [s for s in by_workspace("buying_signals", wid) if s["id"] in (o.get("signal_ids") or [])]
    market = [m for m in by_workspace("market_signals", wid) if m.get("opportunity_id") == oid]
    lead = get_by_id("leads", o.get("lead_id") or "")
    calls = [c for c in by_workspace("calls", wid) if c.get("opportunity_id") == oid or c.get("lead_id") == o.get("lead_id")]
    quals = [q for q in by_workspace("qualifications", wid) if q.get("opportunity_id") == oid or q.get("lead_id") == o.get("lead_id")]
    tasks = [t for t in by_workspace("tasks", wid) if t.get("lead_id") == o.get("lead_id")]
    nbas = demo_ai.next_best_action(quals[-1] if quals else None, o)
    return {
        "opportunity": o,
        "company": company,
        "contact": contact,
        "signals": signals,
        "market_intelligence": market,
        "lead": lead,
        "calls": calls,
        "qualifications": quals,
        "tasks": tasks,
        "next_best_action": nbas,
        "is_demo": True,
    }


@app.post("/api/v1/opportunities/{oid}/analyze")
def analyze_opp(oid: str, wid: str = Depends(workspace_id), user=Depends(current_user)):
    o = get_by_id("opportunities", oid)
    if not o or o.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    profiles = by_workspace("business_profiles", wid)
    if not profiles:
        raise HTTPException(400, "Approve a business profile first")
    signals = [s for s in by_workspace("buying_signals", wid) if s["id"] in (o.get("signal_ids") or [])]
    market = [m for m in by_workspace("market_signals", wid) if m.get("opportunity_id") == oid]
    analysis = demo_ai.analyze_opportunity(profiles[0], o, signals, market)
    updated = update_record(
        "opportunities",
        oid,
        {
            "score": {k: analysis[k] for k in ("label", "total", "service_match", "intent_score", "freshness_score", "technology_match", "company_fit", "disclaimer")},
            "why_match": analysis["why_match"],
            "why_now": analysis["why_now"],
            "risks": analysis["risks"],
            "missing_information": analysis["missing_information"],
            "recommended_action": analysis["recommended_action"],
            "analyzed_at": utcnow(),
        },
    )
    if o.get("lead_id"):
        update_record("leads", o["lead_id"], {"opportunity_score": analysis["total"], "last_updated": utcnow()})
    audit(wid, user["id"], "analyze_opportunity", "opportunity", oid)
    return {"opportunity": updated, "analysis": analysis, "evidence": analysis["evidence"]}


@app.get("/api/v1/buying-signals")
def list_signals(wid: str = Depends(workspace_id)):
    return by_workspace("buying_signals", wid)


@app.get("/api/v1/opportunities/{oid}/market-intelligence")
def market(oid: str, wid: str = Depends(workspace_id)):
    return [m for m in by_workspace("market_signals", wid) if m.get("opportunity_id") == oid]


@app.get("/api/v1/opportunities/{oid}/evidence")
def opp_evidence(oid: str, wid: str = Depends(workspace_id)):
    o = get_by_id("opportunities", oid)
    if not o or o.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    return [s for s in by_workspace("buying_signals", wid) if s["id"] in (o.get("signal_ids") or [])]


@app.get("/api/v1/opportunities/{oid}/enrichment")
def opp_enrichment(oid: str, wid: str = Depends(workspace_id)):
    o = get_by_id("opportunities", oid)
    if not o or o.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    company = get_by_id("companies", o.get("company_id") or "")
    contact = get_by_id("contacts", o.get("contact_id") or "") if o.get("contact_id") else None
    return {"company": company, "contact": contact, "is_demo": True}


@app.get("/api/v1/leads")
def list_leads(
    wid: str = Depends(workspace_id),
    q: str | None = None,
    stage: str | None = None,
    industry: str | None = None,
    location: str | None = None,
    source: str | None = None,
    intent: str | None = None,
    min_score: int | None = None,
    sort: str = "-opportunity_score",
):
    rows = by_workspace("leads", wid)
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in " ".join(str(r.get(k) or "") for k in ("name", "company", "email", "notes")).lower()]
    if stage:
        rows = [r for r in rows if r.get("pipeline_stage") == stage]
    if industry:
        rows = [r for r in rows if (r.get("industry") or "").lower() == industry.lower()]
    if location:
        rows = [r for r in rows if location.lower() in (r.get("location") or "").lower()]
    if source:
        rows = [r for r in rows if (r.get("source") or "") == source]
    if intent:
        rows = [r for r in rows if (r.get("intent_level") or "") == intent]
    if min_score is not None:
        rows = [r for r in rows if (r.get("opportunity_score") or 0) >= min_score]
    reverse = sort.startswith("-")
    key = sort.lstrip("-")
    rows.sort(key=lambda r: r.get(key) or 0 if key == "opportunity_score" else str(r.get(key) or ""), reverse=reverse)
    return rows


@app.get("/api/v1/leads/pipeline")
def pipeline(wid: str = Depends(workspace_id)):
    stages = ["discovered", "reviewed", "contacted", "qualified", "meeting", "proposal", "won", "lost"]
    rows = by_workspace("leads", wid)
    return {s: [r for r in rows if r.get("pipeline_stage") == s] for s in stages}


@app.get("/api/v1/leads/{lid}")
def get_lead(lid: str, wid: str = Depends(workspace_id)):
    lead = get_by_id("leads", lid)
    if not lead or lead.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    company = get_by_id("companies", lead.get("company_id") or "")
    contact = get_by_id("contacts", lead.get("contact_id") or "") if lead.get("contact_id") else None
    opp = get_by_id("opportunities", lead.get("opportunity_id") or "")
    calls = [c for c in by_workspace("calls", wid) if c.get("lead_id") == lid]
    quals = [q for q in by_workspace("qualifications", wid) if q.get("lead_id") == lid]
    notes_timeline = [
        {"type": "created", "at": lead.get("created_at"), "text": "Lead created"},
        *[{"type": "call", "at": c.get("started_at"), "text": f"Call {c.get('outcome')}"} for c in calls],
    ]
    enrichment = {
        "company": {"value": lead.get("company"), "source": lead.get("source"), "confidence": 0.8, "last_updated": lead.get("last_updated")},
        "website": {"value": lead.get("website"), "source": lead.get("source"), "confidence": 0.7, "last_updated": lead.get("last_updated")},
        "industry": {"value": lead.get("industry"), "source": lead.get("source"), "confidence": 0.7, "last_updated": lead.get("last_updated")},
        "company_size": {"value": (company or {}).get("company_size"), "source": (company or {}).get("source"), "confidence": (company or {}).get("confidence"), "last_updated": (company or {}).get("last_updated")},
        "location": {"value": lead.get("location"), "source": lead.get("source"), "confidence": 0.7, "last_updated": lead.get("last_updated")},
        "technology": {"value": (company or {}).get("technologies"), "source": (company or {}).get("source"), "confidence": (company or {}).get("confidence"), "last_updated": (company or {}).get("last_updated")},
        "description": {"value": (company or {}).get("description"), "source": (company or {}).get("source"), "confidence": (company or {}).get("confidence"), "last_updated": (company or {}).get("last_updated")},
        "contact": {
            "value": {"name": lead.get("name"), "email": lead.get("email"), "phone": lead.get("phone")} if lead.get("email") or lead.get("phone") else None,
            "source": contact.get("source") if contact else None,
            "confidence": contact.get("confidence") if contact else None,
            "last_updated": contact.get("last_updated") if contact else None,
            "note": None if (lead.get("email") or lead.get("phone")) else "Contact information not publicly available.",
        },
    }
    return {"lead": lead, "company": company, "contact": contact, "opportunity": opp, "calls": calls, "qualifications": quals, "timeline": notes_timeline, "enrichment": enrichment}


@app.post("/api/v1/leads")
def create_lead(body: LeadIn, wid: str = Depends(workspace_id), user=Depends(current_user)):
    rec = create_record(
        "leads",
        {
            "id": new_id("lead"),
            "workspace_id": wid,
            **body.model_dump(),
            "pipeline_stage": "reviewed",
            "source": "manual",
            "intent_level": "unknown",
            "opportunity_score": None,
            "qualification_status": "not_started",
            "campaign_ids": [],
            "is_demo": True,
            "created_at": utcnow(),
            "last_updated": utcnow(),
        },
    )
    audit(wid, user["id"], "create_lead", "lead", rec["id"])
    return rec


@app.patch("/api/v1/leads/{lid}")
def patch_lead(lid: str, payload: dict, wid: str = Depends(workspace_id)):
    lead = get_by_id("leads", lid)
    if not lead or lead.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    payload["last_updated"] = utcnow()
    return update_record("leads", lid, payload)


def _parse_table(content: bytes, filename: str) -> list[dict]:
    name = (filename or "").lower()
    if name.endswith(".xlsx"):
        from openpyxl import load_workbook

        wb = load_workbook(BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        headers = [str(h or "").strip().lower() for h in next(rows_iter, [])]
        out = []
        for parts in rows_iter:
            out.append({headers[i]: str(parts[i]).strip() if i < len(parts) and parts[i] is not None else "" for i in range(len(headers))})
        return out
    text = content.decode("utf-8-sig", errors="ignore")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    headers = [h.strip().lower() for h in lines[0].split(",")]
    rows = []
    for ln in lines[1:]:
        parts = [p.strip() for p in ln.split(",")]
        rows.append({headers[i] if i < len(headers) else f"col{i}": parts[i] if i < len(parts) else "" for i in range(max(len(headers), len(parts)))})
    return rows


FIELD_ALIASES = {
    "name": ["name", "full name", "contact", "contact name"],
    "company": ["company", "company name", "organization"],
    "email": ["email", "e-mail", "work email"],
    "phone": ["phone", "mobile", "phone number"],
    "job_title": ["job title", "title", "role"],
    "website": ["website", "url", "company website"],
    "location": ["location", "city", "country"],
    "industry": ["industry"],
    "notes": ["notes", "comment"],
}


@app.post("/api/v1/leads/import/preview")
async def import_preview(file: UploadFile = File(...), wid: str = Depends(workspace_id)):
    content = await file.read()
    rows = _parse_table(content, file.filename or "file.csv")
    headers = list(rows[0].keys()) if rows else []
    mapping = {}
    for field, aliases in FIELD_ALIASES.items():
        for h in headers:
            if h in aliases:
                mapping[field] = h
                break
    existing_emails = {l.get("email") for l in by_workspace("leads", wid) if l.get("email")}
    preview = []
    for r in rows[:50]:
        email = r.get(mapping.get("email") or "email") or ""
        preview.append({"row": r, "duplicate": email in existing_emails, "valid": bool(r.get(mapping.get("company") or "company") or r.get(mapping.get("email") or "email"))})
    return {"headers": headers, "mapping": mapping, "preview": preview, "count": len(rows)}


class ImportCommit(BaseModel):
    mapping: dict
    rows: list[dict]


@app.post("/api/v1/leads/import")
def import_commit(body: ImportCommit, wid: str = Depends(workspace_id), user=Depends(current_user)):
    existing_emails = {l.get("email") for l in by_workspace("leads", wid) if l.get("email")}
    created = []
    skipped = []
    for r in body.rows:
        mapped = {f: r.get(col) for f, col in body.mapping.items()}
        email = mapped.get("email") or ""
        if email and email in existing_emails:
            skipped.append({"reason": "duplicate", "email": email})
            continue
        if not mapped.get("company") and not email:
            skipped.append({"reason": "invalid", "row": r})
            continue
        rec = create_record(
            "leads",
            {
                "id": new_id("lead"),
                "workspace_id": wid,
                "name": mapped.get("name"),
                "company": mapped.get("company"),
                "email": email or None,
                "phone": mapped.get("phone"),
                "job_title": mapped.get("job_title"),
                "website": mapped.get("website"),
                "location": mapped.get("location"),
                "industry": mapped.get("industry"),
                "notes": mapped.get("notes") or "Imported",
                "pipeline_stage": "reviewed",
                "source": "CSV import",
                "intent_level": "unknown",
                "opportunity_score": None,
                "qualification_status": "not_started",
                "campaign_ids": [],
                "is_demo": True,
                "created_at": utcnow(),
                "last_updated": utcnow(),
            },
        )
        if email:
            existing_emails.add(email)
        created.append(rec)
    audit(wid, user["id"], "import_leads", "lead", None, {"created": len(created)})
    return {"created": created, "skipped": skipped}


@app.get("/api/v1/segments")
def list_segments(wid: str = Depends(workspace_id)):
    segs = by_workspace("lead_segments", wid)
    leads = by_workspace("leads", wid)
    out = []
    for s in segs:
        f = s.get("filters") or {}
        if s.get("type") == "static":
            ids = set(s.get("lead_ids") or [])
            matched = [l for l in leads if l["id"] in ids]
        else:
            matched = leads
            if f.get("location_contains"):
                matched = [l for l in matched if f["location_contains"].lower() in (l.get("location") or "").lower()]
            if f.get("industry"):
                matched = [l for l in matched if (l.get("industry") or "") == f["industry"]]
            if f.get("min_score") is not None:
                matched = [l for l in matched if (l.get("opportunity_score") or 0) >= f["min_score"]]
            if f.get("intent_level"):
                matched = [l for l in matched if l.get("intent_level") == f["intent_level"]]
            if f.get("source"):
                matched = [l for l in matched if l.get("source") == f["source"]]
            if f.get("qualification_status"):
                matched = [l for l in matched if l.get("qualification_status") == f["qualification_status"]]
        out.append({**s, "leads": matched, "count": len(matched)})
    return out


@app.post("/api/v1/segments")
def create_segment(body: SegmentIn, wid: str = Depends(workspace_id)):
    return create_record(
        "lead_segments",
        {"id": new_id("seg"), "workspace_id": wid, **body.model_dump(), "created_at": utcnow()},
    )


@app.post("/api/v1/segments/preview")
def preview_segment(body: SegmentIn, wid: str = Depends(workspace_id)):
    fake = {"filters": body.filters, "type": body.type, "lead_ids": body.lead_ids, "workspace_id": wid, "name": body.name}
    # reuse list logic
    segs = [fake]
    leads = by_workspace("leads", wid)
    f = body.filters
    matched = leads
    if f.get("location_contains"):
        matched = [l for l in matched if f["location_contains"].lower() in (l.get("location") or "").lower()]
    if f.get("min_score") is not None:
        matched = [l for l in matched if (l.get("opportunity_score") or 0) >= f["min_score"]]
    return {"count": len(matched), "leads": matched}


@app.get("/api/v1/voice-agents")
def list_agents(wid: str = Depends(workspace_id)):
    return by_workspace("voice_agents", wid)


@app.get("/api/v1/voice-agents/{aid}")
def get_agent(aid: str, wid: str = Depends(workspace_id)):
    a = get_by_id("voice_agents", aid)
    if not a or a.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    return a


@app.post("/api/v1/voice-agents")
def create_agent(body: AgentIn, wid: str = Depends(workspace_id), user=Depends(current_user)):
    rec = create_record(
        "voice_agents",
        {
            "id": new_id("agent"),
            "workspace_id": wid,
            **body.model_dump(),
            "safety": {
                "disclose_ai": True,
                "handoff_phrases": ["speak to a human"],
                "opt_out_phrases": ["do not call"],
            },
            "approved_voicemail": "Hello, this is an AI assistant. Please call us back. Thank you.",
            "is_demo": True,
            "created_at": utcnow(),
        },
    )
    audit(wid, user["id"], "create_agent", "voice_agent", rec["id"])
    return rec


@app.patch("/api/v1/voice-agents/{aid}")
def patch_agent(aid: str, payload: dict, wid: str = Depends(workspace_id)):
    a = get_by_id("voice_agents", aid)
    if not a or a.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    return update_record("voice_agents", aid, payload)


@app.delete("/api/v1/voice-agents/{aid}")
def delete_agent(aid: str, wid: str = Depends(workspace_id)):
    a = get_by_id("voice_agents", aid)
    if not a or a.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    delete_record("voice_agents", aid)
    return {"ok": True}


@app.post("/api/v1/voice-agents/{aid}/playground")
def playground(aid: str, body: PlaygroundIn, wid: str = Depends(workspace_id)):
    agent = get_by_id("voice_agents", aid)
    if not agent or agent.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    history = body.history
    if not history:
        history = [{"speaker": "agent", "text": opening_message(agent, body.language), "ts": utcnow()}]
    result = agent_reply(agent, body.message, history, body.language)
    result["label"] = "Demo Voice Simulation"
    return result


@app.get("/api/v1/campaigns")
def list_campaigns(wid: str = Depends(workspace_id)):
    return by_workspace("campaigns", wid)


@app.get("/api/v1/campaigns/{cid}")
def get_campaign(cid: str, wid: str = Depends(workspace_id)):
    c = get_by_id("campaigns", cid)
    if not c or c.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    return c


@app.post("/api/v1/campaigns")
def create_campaign(body: CampaignIn, wid: str = Depends(workspace_id), user=Depends(current_user)):
    rec = create_record(
        "campaigns",
        {
            "id": new_id("camp"),
            "workspace_id": wid,
            **body.model_dump(),
            "retry_policy": body.retry_policy or {"max_attempts": 2, "on": ["No Answer", "Voicemail"]},
            "status": "draft",
            "is_demo": True,
            "created_at": utcnow(),
        },
    )
    audit(wid, user["id"], "create_campaign", "campaign", rec["id"])
    return rec


@app.post("/api/v1/campaigns/{cid}/launch")
def launch_campaign(cid: str, wid: str = Depends(workspace_id), user=Depends(current_user)):
    c = get_by_id("campaigns", cid)
    if not c or c.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    ws = get_by_id("workspaces", wid)
    mode = (ws or {}).get("mode") or "demo"
    if mode == "live":
        raise HTTPException(400, "Live calling is not configured. Switch to DEMO MODE.")
    status = "running" if c.get("schedule") == "immediate" else "scheduled"
    updated = update_record("campaigns", cid, {"status": status, "launched_at": utcnow(), "mode": "demo"})
    audit(wid, user["id"], "launch_campaign", "campaign", cid)
    return updated


@app.post("/api/v1/campaigns/{cid}/pause")
def pause_campaign(cid: str, wid: str = Depends(workspace_id)):
    return update_record("campaigns", cid, {"status": "paused"})


@app.post("/api/v1/campaigns/{cid}/resume")
def resume_campaign(cid: str, wid: str = Depends(workspace_id)):
    return update_record("campaigns", cid, {"status": "running"})


class SimulateCallIn(BaseModel):
    lead_id: str
    prospect_script: str | None = None
    outcome_hint: str | None = None
    language: str = "en"


@app.post("/api/v1/campaigns/{cid}/calls/simulate")
def simulate_call(cid: str, body: SimulateCallIn, wid: str = Depends(workspace_id), user=Depends(current_user)):
    campaign = get_by_id("campaigns", cid)
    if not campaign or campaign.get("workspace_id") != wid:
        raise HTTPException(404, "Campaign not found")
    lead = get_by_id("leads", body.lead_id)
    if not lead or lead.get("workspace_id") != wid:
        raise HTTPException(404, "Lead not found")
    if lead.get("phone"):
        blocked = any(o.get("phone") == lead.get("phone") for o in by_workspace("opt_outs", wid))
        if blocked:
            raise HTTPException(400, "Lead is on the do-not-contact list")
    agent = get_by_id("voice_agents", campaign.get("agent_id"))
    if not agent:
        raise HTTPException(400, "Agent missing")
    hint = body.outcome_hint
    script = body.prospect_script
    if not script:
        if hint == "Voicemail":
            script = ""
        elif hint == "Not Interested":
            script = "I am not interested. Do not call again."
        elif hint == "Callback Requested":
            script = "I want a callback."
        else:
            script = "We are looking for SharePoint migration support and want to start this month."
    history = [{"speaker": "agent", "text": opening_message(agent, body.language), "ts": utcnow()}]
    if hint == "Voicemail" or script.strip() == "":
        result = agent_reply(agent, "voicemail", history, body.language)
        result["outcome"] = "Voicemail"
        result["qualification"]["interest_level"] = "Unknown"
        result["qualification"]["high_intent"] = False
    else:
        result = agent_reply(agent, script, history, body.language)
    outcome = result.get("outcome") or ("Interested" if result["qualification"].get("high_intent") else "Connected")
    call = create_record(
        "calls",
        {
            "id": new_id("call"),
            "workspace_id": wid,
            "campaign_id": cid,
            "lead_id": lead["id"],
            "opportunity_id": lead.get("opportunity_id"),
            "agent_id": agent["id"],
            "mode": "demo",
            "label": "Demo Voice Simulation",
            "outcome": outcome,
            "duration_sec": 42 if outcome not in ("Voicemail", "No Answer") else 8,
            "language": body.language,
            "stop_reason": result.get("stop_reason"),
            "escalated": result.get("escalated"),
            "voicemail_message": agent.get("approved_voicemail") if outcome == "Voicemail" else None,
            "started_at": utcnow(),
            "is_demo": True,
        },
    )
    transcript = create_record(
        "transcripts",
        {
            "id": new_id("tr"),
            "workspace_id": wid,
            "call_id": call["id"],
            "turns": result["history"],
            "summary": _summarize(result, lead),
            "requirements": result["qualification"].get("requirements"),
            "objections": "Internal IT team" if "internal" in script.lower() else None,
            "interest_level": result["qualification"].get("interest_level"),
            "recommended_action": demo_ai.next_best_action(result["qualification"], get_by_id("opportunities", lead.get("opportunity_id") or "")),
        },
    )
    qual = create_record(
        "qualifications",
        {
            "id": new_id("qual"),
            "workspace_id": wid,
            "call_id": call["id"],
            "lead_id": lead["id"],
            "opportunity_id": lead.get("opportunity_id"),
            **result["qualification"],
            "created_at": utcnow(),
            "is_demo": True,
        },
    )
    intent = result["qualification"].get("interest_level") or "unknown"
    stage = lead.get("pipeline_stage")
    if result["qualification"].get("high_intent"):
        stage = "qualified"
        intent_store = "interested"
    elif intent == "Not Interested":
        stage = "lost"
        intent_store = "Not Interested"
        create_record("opt_outs", {"id": new_id("opt"), "workspace_id": wid, "phone": lead.get("phone"), "email": lead.get("email"), "reason": "opt_out", "created_at": utcnow()})
    elif intent == "Callback":
        stage = "contacted"
        intent_store = "Callback"
    else:
        stage = "contacted"
        intent_store = intent
    update_record(
        "leads",
        lead["id"],
        {
            "pipeline_stage": stage,
            "intent_level": intent_store,
            "qualification_status": "complete",
            "last_updated": utcnow(),
            "campaign_ids": list(set((lead.get("campaign_ids") or []) + [cid])),
        },
    )
    task = None
    if result["qualification"].get("high_intent") or result.get("escalated") or intent == "Callback":
        due = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()
        task = create_record(
            "tasks",
            {
                "id": new_id("task"),
                "workspace_id": wid,
                "title": f"Follow up with {lead.get('company')}",
                "priority": "HIGH",
                "due": due,
                "reason": (result["qualification"].get("banner_reason") or script)[:200],
                "status": "open",
                "assignee": user.get("name"),
                "lead_id": lead["id"],
                "opportunity_id": lead.get("opportunity_id"),
                "created_at": utcnow(),
                "is_demo": True,
            },
        )
        create_record(
            "notifications",
            {
                "id": new_id("ntf"),
                "workspace_id": wid,
                "type": "high_intent",
                "title": "HIGH INTENT PROSPECT" if result["qualification"].get("high_intent") else "Follow-up needed",
                "body": task["reason"],
                "opportunity_id": lead.get("opportunity_id"),
                "read": False,
                "is_demo": True,
                "created_at": utcnow(),
            },
        )
    _bump_analytics(wid, outcome, call["duration_sec"])
    audit(wid, user["id"], "simulate_call", "call", call["id"])
    return {
        "label": "Demo Voice Simulation",
        "call": call,
        "transcript": transcript,
        "qualification": qual,
        "task": task,
        "next_best_action": transcript["recommended_action"],
        "agent_turns": result["history"],
    }


def _summarize(result: dict, lead: dict) -> str:
    q = result.get("qualification") or {}
    return (
        f"Demo simulation with {lead.get('company')}. Interest: {q.get('interest_level')}. "
        f"Requirements: {q.get('requirements') or 'not captured'}. Timeline: {q.get('timeline') or 'not captured'}."
    )


def _bump_analytics(wid: str, outcome: str, duration: int) -> None:
    data = read_json("analytics")
    if not isinstance(data, dict):
        data = {}
    row = data.get(wid) or {
        "calls_attempted": 0,
        "connected": 0,
        "voicemail": 0,
        "qualification_rate": 0,
        "interested": 0,
        "callbacks": 0,
        "opt_outs": 0,
        "avg_duration_sec": 0,
        "series": [],
    }
    row["calls_attempted"] = row.get("calls_attempted", 0) + 1
    if outcome == "Voicemail":
        row["voicemail"] = row.get("voicemail", 0) + 1
    elif outcome != "No Answer":
        row["connected"] = row.get("connected", 0) + 1
    if outcome == "Interested":
        row["interested"] = row.get("interested", 0) + 1
    if outcome == "Callback Requested":
        row["callbacks"] = row.get("callbacks", 0) + 1
    if outcome == "Not Interested":
        row["opt_outs"] = row.get("opt_outs", 0) + 1
    n = row["calls_attempted"]
    row["avg_duration_sec"] = round(((row.get("avg_duration_sec") or 0) * (n - 1) + duration) / n)
    row["qualification_rate"] = round(100 * (row.get("interested", 0) + row.get("callbacks", 0)) / n)
    series = row.get("series") or []
    day = utcnow()[:10]
    found = next((s for s in series if s.get("date") == day), None)
    if found:
        found["calls"] = found.get("calls", 0) + 1
    else:
        series.append({"date": day, "calls": 1})
    row["series"] = series
    data[wid] = row
    write_json("analytics", data)


@app.get("/api/v1/calls")
def list_calls(wid: str = Depends(workspace_id)):
    return by_workspace("calls", wid)


@app.get("/api/v1/calls/{call_id}")
def get_call(call_id: str, wid: str = Depends(workspace_id)):
    c = get_by_id("calls", call_id)
    if not c or c.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    tr = next((t for t in by_workspace("transcripts", wid) if t.get("call_id") == call_id), None)
    qual = next((q for q in by_workspace("qualifications", wid) if q.get("call_id") == call_id), None)
    return {"call": c, "transcript": tr, "qualification": qual}


@app.get("/api/v1/calls/{call_id}/transcript")
def get_transcript(call_id: str, wid: str = Depends(workspace_id)):
    c = get_by_id("calls", call_id)
    if not c or c.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    tr = next((t for t in by_workspace("transcripts", wid) if t.get("call_id") == call_id), None)
    if not tr:
        raise HTTPException(404, "Transcript not found")
    return tr


@app.post("/api/v1/calls/{call_id}/handoff")
def handoff(call_id: str, wid: str = Depends(workspace_id), user=Depends(current_user)):
    c = get_by_id("calls", call_id)
    if not c or c.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    update_record("calls", call_id, {"escalated": True, "stop_reason": "human_handoff"})
    lead = get_by_id("leads", c.get("lead_id"))
    task = create_record(
        "tasks",
        {
            "id": new_id("task"),
            "workspace_id": wid,
            "title": f"Human handoff: {lead.get('company') if lead else 'prospect'}",
            "priority": "HIGH",
            "due": (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat(),
            "reason": "Immediate human handoff requested.",
            "status": "open",
            "assignee": user.get("name"),
            "lead_id": c.get("lead_id"),
            "created_at": utcnow(),
            "is_demo": True,
        },
    )
    return {"call": get_by_id("calls", call_id), "task": task}


@app.post("/api/v1/calls/{call_id}/opt-out")
def opt_out(call_id: str, wid: str = Depends(workspace_id)):
    c = get_by_id("calls", call_id)
    if not c:
        raise HTTPException(404, "Not found")
    lead = get_by_id("leads", c.get("lead_id"))
    create_record("opt_outs", {"id": new_id("opt"), "workspace_id": wid, "phone": (lead or {}).get("phone"), "reason": "opt_out", "created_at": utcnow()})
    update_record("calls", call_id, {"stop_reason": "opt_out", "outcome": "Not Interested"})
    return {"ok": True}


@app.get("/api/v1/tasks")
def list_tasks(wid: str = Depends(workspace_id)):
    return by_workspace("tasks", wid)


@app.post("/api/v1/tasks")
def create_task(payload: dict, wid: str = Depends(workspace_id)):
    return create_record("tasks", {**payload, "id": new_id("task"), "workspace_id": wid, "created_at": utcnow(), "status": payload.get("status") or "open"})


@app.patch("/api/v1/tasks/{tid}")
def patch_task(tid: str, body: TaskPatch, wid: str = Depends(workspace_id)):
    t = get_by_id("tasks", tid)
    if not t or t.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    return update_record("tasks", tid, {k: v for k, v in body.model_dump().items() if v is not None})


@app.post("/api/v1/copilot/ask")
def copilot(body: CopilotIn, wid: str = Depends(workspace_id)):
    return demo_ai.copilot(body.question, wid)


@app.get("/api/v1/dashboard")
def dashboard(wid: str = Depends(workspace_id)):
    leads = by_workspace("leads", wid)
    opps = by_workspace("opportunities", wid)
    campaigns = by_workspace("campaigns", wid)
    calls = by_workspace("calls", wid)
    tasks = [t for t in by_workspace("tasks", wid) if t.get("status") != "complete"]
    high = [l for l in leads if (l.get("intent_level") or "").lower() in ("interested", "high") or (l.get("opportunity_score") or 0) >= 85]
    insights = []
    if high:
        insights.append(f"{len(high)} high-intent or high-score opportunities.")
    callbacks = [l for l in leads if l.get("intent_level") == "Callback"]
    if callbacks:
        insights.append(f"{len(callbacks)} prospects requested callbacks.")
    if tasks:
        insights.append(f"{len(tasks)} prospects need follow-up.")
    if not insights:
        insights.append("Launch a demo campaign on ABC Technologies to generate live insights.")
    return {
        "totals": {
            "opportunities": len(opps),
            "high_intent": len(high),
            "qualified_leads": len([l for l in leads if l.get("pipeline_stage") == "qualified"]),
            "active_campaigns": len([c for c in campaigns if c.get("status") in ("running", "scheduled")]),
            "calls": len(calls),
            "meetings": len([l for l in leads if l.get("pipeline_stage") == "meeting"]),
            "follow_ups": len(tasks),
        },
        "insights": insights,
        "recent_opportunities": sorted(opps, key=lambda o: o.get("discovered_at") or "", reverse=True)[:5],
        "campaigns": campaigns,
        "next_actions": tasks[:5],
    }


@app.get("/api/v1/analytics/calls")
def analytics(wid: str = Depends(workspace_id)):
    data = read_json("analytics")
    row = data.get(wid) if isinstance(data, dict) else None
    leads = by_workspace("leads", wid)
    sources: dict[str, int] = defaultdict(int)
    for l in leads:
        sources[l.get("source") or "unknown"] += 1
    quals = by_workspace("qualifications", wid)
    outcomes: dict[str, int] = defaultdict(int)
    for q in quals:
        outcomes[q.get("interest_level") or "Unknown"] += 1
    campaigns = by_workspace("campaigns", wid)
    return {
        "kpis": row or {},
        "calls_over_time": (row or {}).get("series") or [],
        "lead_sources": [{"source": k, "count": v} for k, v in sources.items()],
        "qualification_outcomes": [{"outcome": k, "count": v} for k, v in outcomes.items()],
        "campaign_performance": [{"name": c.get("name"), "status": c.get("status"), "leads": len(c.get("lead_ids") or [])} for c in campaigns],
    }


@app.get("/api/v1/saved-searches")
def list_searches(wid: str = Depends(workspace_id)):
    return by_workspace("saved_searches", wid)


@app.post("/api/v1/saved-searches")
def create_search(body: SavedSearchIn, wid: str = Depends(workspace_id)):
    return create_record("saved_searches", {"id": new_id("search"), "workspace_id": wid, **body.model_dump(), "last_run_at": None, "created_at": utcnow()})


@app.patch("/api/v1/saved-searches/{sid}")
def patch_search(sid: str, payload: dict, wid: str = Depends(workspace_id)):
    s = get_by_id("saved_searches", sid)
    if not s or s.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    return update_record("saved_searches", sid, payload)


@app.post("/api/v1/saved-searches/{sid}/run")
def run_search(sid: str, wid: str = Depends(workspace_id)):
    s = get_by_id("saved_searches", sid)
    if not s or s.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    criteria = demo_ai.plan_search(s.get("query") or "")
    matches = ADAPTERS[0].search(wid, criteria)
    update_record("saved_searches", sid, {"last_run_at": utcnow()})
    ntf = None
    if matches:
        top = matches[0]
        ntf = create_record(
            "notifications",
            {
                "id": new_id("ntf"),
                "workspace_id": wid,
                "type": "radar",
                "title": "New high-intent opportunity detected",
                "body": f"{top.get('title') or top.get('requirement')} matched “{s.get('name')}”. DEMO DATA.",
                "opportunity_id": top.get("id") if str(top.get("id", "")).startswith("opp_") else None,
                "saved_search_id": sid,
                "read": False,
                "is_demo": True,
                "created_at": utcnow(),
            },
        )
    return {"matches": matches, "notification": ntf, "label": "DEMO DATA"}


@app.get("/api/v1/notifications")
def list_ntf(wid: str = Depends(workspace_id)):
    return sorted(by_workspace("notifications", wid), key=lambda n: n.get("created_at") or "", reverse=True)


@app.post("/api/v1/notifications/{nid}/read")
def read_ntf(nid: str, wid: str = Depends(workspace_id)):
    n = get_by_id("notifications", nid)
    if not n or n.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    return update_record("notifications", nid, {"read": True})


@app.get("/api/v1/admin/users")
def admin_users(_: dict = Depends(require_admin)):
    return [strip_user(u) for u in get_all("users")]


@app.get("/api/v1/admin/workspaces")
def admin_ws(_: dict = Depends(require_admin)):
    return get_all("workspaces")


@app.get("/api/v1/admin/campaigns")
def admin_camps(_: dict = Depends(require_admin)):
    return get_all("campaigns")


@app.get("/api/v1/admin/calls")
def admin_calls(_: dict = Depends(require_admin)):
    return get_all("calls")


@app.get("/api/v1/admin/usage")
def admin_usage(_: dict = Depends(require_admin)):
    return {"analytics": read_json("analytics"), "users": len(get_all("users")), "calls": len(get_all("calls"))}


@app.get("/api/v1/admin/audit-logs")
def admin_audit(_: dict = Depends(require_admin)):
    return sorted(get_all("audit_logs"), key=lambda a: a.get("created_at") or "", reverse=True)[:200]


@app.get("/api/v1/opt-outs")
def list_opt(wid: str = Depends(workspace_id)):
    return by_workspace("opt_outs", wid)
