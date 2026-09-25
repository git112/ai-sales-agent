from __future__ import annotations

import json
import logging
import os
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, EmailStr, Field

from app.ai import get_ai
from app.campaign_sim import next_step_plan
from app.core.config import settings
from app.core.security import create_token, hash_password, verify_password
from app.deps import current_user, require_admin, workspace_id
from app.export_leads import flatten_lead, to_csv, to_xlsx
from app.import_validate import validate_import_rows
from app.knowledge import UPLOAD_ROOT, extract_text, knowledge_store
from app.repositories import notifications_repo, segments_repo
from app.sanitize import client_patch, safe_dest
from app.segmentation import apply_segment
from app.sources import ADAPTERS
from app.store import (
    audit,
    by_workspace,
    create_record,
    delete_record,
    filter_records,
    get_all,
    get_by_id,
    init_datastore,
    new_id,
    read_json,
    search_records,
    sqlite_active,
    update_record,
    utcnow,
    write_json,
)
from app.url_analysis import analyze_website, validate_url
from app.voice import agent_reply, opening_message, scripts
from app import bolna as bolna_client
from app.live_voice import live_voice
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_datastore()
    yield


app = FastAPI(title="Lumina API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_rate: dict[str, list[float]] = defaultdict(list)

# Temporary placeholder email applied to leads that don't have one on file.
# Used so the Calendly "send confirmation email" path always has a recipient.
# Override with DEFAULT_LEAD_EMAIL in .env when proper emails are collected.
DEFAULT_LEAD_EMAIL = os.getenv("DEFAULT_LEAD_EMAIL", "23it021@charusat.edu.in")


def _resolve_lead_email(provided: str | None) -> str:
    """Return a usable email for a lead — falls back to DEFAULT_LEAD_EMAIL when missing."""
    p = (provided or "").strip()
    return p or DEFAULT_LEAD_EMAIL


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


log = logging.getLogger("lumina.api")


@app.exception_handler(StarletteHTTPException)
async def http_error(_, exc: StarletteHTTPException):
    return JSONResponse({"error": {"code": "http_error", "message": exc.detail}}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def valid_error(_, exc: RequestValidationError):
    return JSONResponse({"error": {"code": "validation_error", "message": "Invalid request"}}, status_code=422)


@app.exception_handler(Exception)
async def on_error(_, exc: Exception):
    log.warning("Unhandled %s", type(exc).__name__)
    return JSONResponse({"error": {"code": "server_error", "message": "Unexpected error"}}, status_code=500)


def strip_user(u: dict) -> dict:
    out = {k: v for k, v in u.items() if k != "password_hash"}
    return out


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class ForgotIn(BaseModel):
    email: EmailStr


class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class AnalyzeUrlIn(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    refresh: bool = False


class OnboardingIn(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    website: str | None = Field(default=None, max_length=2048)
    description: str | None = Field(default=None, max_length=8000)
    industry: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=200)
    products: list[str] = []
    services: list[str] = []
    technologies: list[str] = []
    target_industries: list[str] = []
    target_locations: list[str] = []
    company_size: str | None = None
    target_roles: list[str] = []
    keywords: list[str] = []


class SearchIn(BaseModel):
    query: str = Field(min_length=1, max_length=500)


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
    start_date: str | None = None
    start_time: str | None = None
    timezone: str = "Asia/Kolkata"
    retry_policy: dict | None = None
    quiet_hours: dict | None = None


class AgentIn(BaseModel):
    name: str
    purpose: str | None = None
    language: str = "en"
    voice: str = "professional_female"
    tone: str = "consultative"
    knowledge_doc_ids: list[str] = []
    call_objective: str | None = None
    qualification_questions: list[str] = []
    company_name: str | None = None
    guardrails: list[str] = []
    guardrail_hours: dict | None = None


class PlaygroundIn(BaseModel):
    message: str = Field(min_length=0, max_length=4000)
    history: list[dict] = Field(default_factory=list, max_length=40)
    language: str = "en"


class CopilotIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class SavedSearchIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    query: str = Field(min_length=1, max_length=500)
    filters: dict = {}
    source: str = "Enterprise Signal Network"
    frequency: str = "daily"
    status: str = "active"


class SegmentIn(BaseModel):
    name: str
    type: str = "dynamic"
    filters: Any = {}
    lead_ids: list[str] = []
    active: bool = True


class TaskPatch(BaseModel):
    status: str | None = None
    assignee: str | None = None
    due: str | None = None
    title: str | None = None


@app.get("/health")
def health():
    return {"ok": True, "mode": settings.default_app_mode, "datastore": "sqlite" if sqlite_active() else "json"}


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
    if user.get("status") == "suspended":
        raise HTTPException(403, "Account suspended")
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
        raise HTTPException(404, "Not found")
    update_record("users", user["id"], {"workspace_id": wid})
    token = create_token({"sub": user["id"], "role": user["role"], "workspace_id": wid})
    return {"token": token, "workspace": ws}


@app.get("/api/v1/workspaces/{wid}/mode")
def get_mode(wid: str, user=Depends(current_user)):
    ws = get_by_id("workspaces", wid)
    if not ws:
        raise HTTPException(404, "Workspace not found")
    if user.get("role") != "admin" and ws.get("owner_user_id") != user["id"] and wid != user.get("workspace_id"):
        raise HTTPException(404, "Not found")
    return {"mode": ws.get("mode"), "is_demo": ws.get("mode") == "demo"}


@app.patch("/api/v1/workspaces/{wid}/mode")
def set_mode(wid: str, mode: str = Form(...), user=Depends(current_user)):
    if mode not in ("demo", "live"):
        raise HTTPException(400, "mode must be demo or live")
    ws = get_by_id("workspaces", wid)
    if not ws:
        raise HTTPException(404, "Not found")
    if user.get("role") != "admin" and ws.get("owner_user_id") != user["id"] and wid != user.get("workspace_id"):
        raise HTTPException(404, "Not found")
    if mode == "live" and not bolna_client.is_configured():
        raise HTTPException(400, "Cannot switch to live mode: BOLNA_API_KEY is not set on the server.")
    ws = update_record("workspaces", wid, {"mode": mode})
    audit(wid, user["id"], "set_mode", "workspace", wid, {"mode": mode})
    return ws


class WorkspacePhoneIn(BaseModel):
    from_phone_number: str | None = None


@app.patch("/api/v1/workspaces/{wid}/phone")
def set_workspace_phone(wid: str, body: WorkspacePhoneIn, user=Depends(current_user)):
    ws = get_by_id("workspaces", wid)
    if not ws:
        raise HTTPException(404, "Not found")
    if user.get("role") != "admin" and ws.get("owner_user_id") != user["id"] and wid != user.get("workspace_id"):
        raise HTTPException(404, "Not found")
    phone = (body.from_phone_number or "").strip() or None
    updated = update_record("workspaces", wid, {"from_phone_number": phone})
    audit(wid, user["id"], "set_phone", "workspace", wid, {"from_phone_number": phone})
    return updated


@app.get("/api/v1/business-profile")
def get_profile(wid: str = Depends(workspace_id)):
    rows = by_workspace("business_profiles", wid)
    return rows[0] if rows else None


@app.patch("/api/v1/business-profile")
def patch_profile(payload: dict, wid: str = Depends(workspace_id), user=Depends(current_user)):
    rows = by_workspace("business_profiles", wid)
    if not rows:
        raise HTTPException(404, "No profile")
    patch = client_patch(payload)
    patch["last_updated"] = utcnow()
    rec = update_record("business_profiles", rows[0]["id"], patch)
    audit(wid, user["id"], "patch_profile", "business_profile", rec["id"])
    return rec


@app.post("/api/v1/business-profile/analyze")
def analyze_profile(body: OnboardingIn, wid: str = Depends(workspace_id), user=Depends(current_user)):
    docs = by_workspace("knowledge_documents", wid)
    text = "\n".join(d.get("extracted_text") or "" for d in docs)
    understood = get_ai().understand_business({**body.model_dump(), "documents_text": text, "company_name": body.company_name})
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


@app.post("/api/v1/business-profile/analyze-url")
def analyze_url(body: AnalyzeUrlIn, wid: str = Depends(workspace_id), user=Depends(current_user)):
    try:
        url = validate_url(body.url)
    except ValueError as e:
        raise HTTPException(400, str(e))
    extracted = analyze_website(url, refresh=body.refresh)
    fetch_status = extracted.get("fetch_status") or "failed"
    label = extracted.get("label") or "Not detected"
    source = extracted.get("source") or "Public website fetch"
    confidence = extracted.get("confidence") if extracted.get("confidence") is not None else 0
    understood_fields = dict(extracted)
    if fetch_status == "ok":
        excerpt = (extracted.get("extracted_excerpt") or extracted.get("extracted_title") or "")[:4000]
        understood = get_ai().understand_business(
            {
                "company_name": extracted.get("company_name") or "unknown",
                "website": url,
                "description": excerpt,
                "documents_text": excerpt,
                "services": extracted.get("products_services") or extracted.get("services") or [],
                "technologies": extracted.get("technologies") or [],
                "target_locations": extracted.get("locations") or [],
                "keywords": extracted.get("business_keywords") or [],
            }
        )
        understood_fields["company_summary"] = understood.get("company_summary")
        understood_fields["services"] = understood.get("services") or extracted.get("products_services")
        understood_fields["technologies"] = understood.get("technologies") or extracted.get("technologies")
        understood_fields["buying_signals"] = extracted.get("likely_buying_signals") or understood.get("buying_signals") or []
    elif fetch_status == "failed_fallback":
        understood = get_ai().understand_business(
            {
                "company_name": extracted.get("company_name"),
                "website": url,
                "description": "Microsoft 365 and SharePoint consulting",
                "services": extracted.get("products_services") or [],
                "technologies": extracted.get("technologies") or [],
            }
        )
        understood_fields["company_summary"] = understood.get("company_summary")
        understood_fields["services"] = understood.get("services")
        understood_fields["buying_signals"] = extracted.get("likely_buying_signals") or []
    existing = by_workspace("business_profiles", wid)
    record = {
        "workspace_id": wid,
        "approved": False,
        "is_demo": bool(extracted.get("is_demo")) or label == "DEMO DATA",
        "source_mode": extracted.get("source_mode") or ("demo" if label != "REAL SOURCE" else "real"),
        "source_type": extracted.get("source_type") or "website",
        "source_url": url,
        "retrieved_at": extracted.get("retrieved_at") or utcnow(),
        "company_name": understood_fields.get("company_name"),
        "website": url,
        "industry": understood_fields.get("industry"),
        "location": (understood_fields.get("locations") or [None])[0] if isinstance(understood_fields.get("locations"), list) else understood_fields.get("location"),
        "description": understood_fields.get("extracted_excerpt") or understood_fields.get("company_summary"),
        "services": understood_fields.get("services") or understood_fields.get("products_services") or [],
        "technologies": understood_fields.get("technologies") or [],
        "keywords": understood_fields.get("business_keywords") or [],
        "buying_signals": understood_fields.get("buying_signals") or understood_fields.get("likely_buying_signals") or [],
        "target_customers": understood_fields.get("target_customers") or [],
        "locations": understood_fields.get("locations") or [],
        "likely_pain_points": understood_fields.get("likely_pain_points") or [],
        "facts": understood_fields.get("facts") or [],
        "source": source,
        "confidence": confidence,
        "label": label,
        "fetch_status": fetch_status,
        "fetch_error": extracted.get("fetch_error") if fetch_status != "ok" else None,
        "from_cache": bool(extracted.get("from_cache")),
        "last_updated": utcnow(),
        **{k: v for k, v in understood_fields.items() if k not in ("services", "technologies")},
    }
    if existing:
        record = update_record("business_profiles", existing[0]["id"], record) or {**existing[0], **record}
    else:
        record = create_record("business_profiles", {**record, "id": new_id("profile")})
    audit(wid, user["id"], "analyze_url", "business_profile", record["id"], {"url": url, "fetch_status": fetch_status})
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
    patch = client_patch(payload)
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
    q = (q or "")[:500]
    return {"query": q, "chunks": knowledge_store.search(wid, q)}


@app.post("/api/v1/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...), wid: str = Depends(workspace_id), user=Depends(current_user)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".pdf", ".docx", ".txt"):
        raise HTTPException(400, "Only PDF, DOCX, TXT allowed")
    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(400, "File too large")
    try:
        dest = safe_dest(UPLOAD_ROOT, wid, file.filename or "upload.txt")
    except ValueError:
        raise HTTPException(400, "Invalid filename")
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
    criteria = get_ai().plan_search(body.query)
    results = []
    source_status = []
    for adapter in ADAPTERS:
        try:
            batch = adapter.search(wid, criteria)
            results.extend(batch)
            source_status.append(adapter.status() if hasattr(adapter, "status") else {"name": adapter.name, "discovered": len(batch)})
        except Exception as e:
            source_status.append({"name": adapter.name, "error": str(e)[:200], "discovered": 0, "fallback": "Enterprise Signal Network remains available"})
    seen = set()
    unique = []
    for r in results:
        key = r.get("id") or r.get("source_url") or r.get("title")
        if key in seen:
            continue
        seen.add(key)
        opp_id = r.get("id") or new_id("opp")
        r["id"] = opp_id  # Assign back to r so it's returned to frontend
        existing_opp = get_by_id("opportunities", opp_id)
        if not existing_opp:
            create_record(
                "opportunities",
                {
                    "id": opp_id,
                    "workspace_id": wid,
                    "title": r.get("title") or "Discovered Opportunity",
                    "requirement": r.get("requirement") or r.get("description") or "Not detected",
                    "company": r.get("company") or r.get("company_name"),
                    "company_name": r.get("company_name") or r.get("company"),
                    "source": r.get("source") or r.get("adapter") or "Public Web",
                    "source_url": r.get("source_url") or r.get("original_url"),
                    "published_at": r.get("published_at"),
                    "detected_at": r.get("detected_at") or utcnow(),
                    "location": r.get("location") or "Not detected",
                    "industry": r.get("industry") or "Not detected",
                    "confidence": r.get("confidence") or 0.85,
                    "score": r.get("score") or {
                        "label": "AI Opportunity Score",
                        "total": int(round((r.get("confidence") or 0.85) * 100)),
                        "service_match": 85,
                        "intent_score": 85,
                        "freshness_score": 90,
                        "technology_match": 85,
                        "company_fit": 80,
                    },
                    "label": r.get("label") or "VERIFIED SIGNAL",
                    "is_demo": False,
                    "status": "new",
                },
            )
        unique.append(
            {
                **r,
                "id": opp_id,
                "label": r.get("label") or ("VERIFIED SIGNAL" if r.get("is_demo") else "Source verified"),
                "source": r.get("source") or r.get("adapter") or "Enterprise Signal Network",
                "original_url": r.get("original_url") or r.get("source_url"),
                "detected_at": r.get("detected_at") or r.get("discovered_at") or utcnow(),
                "company_name": r.get("company") or r.get("company_name") or (get_by_id("companies", r.get("company_id") or "") or {}).get("name"),
                "contact": r.get("contact") if r.get("contact") not in (None, "") else "Not detected",
                "confidence": r.get("confidence") if r.get("confidence") is not None else None,
            }
        )
    audit(wid, user["id"], "search_opportunities", "opportunity", None, {"query": body.query})
    return {
        "criteria": criteria,
        "source_note": "Enterprise Signal Network and Public Web feeds are continuously active.",
        "sources": source_status,
        "results": unique,
    }


@app.get("/api/v1/opportunities")
def list_opps(wid: str = Depends(workspace_id)):
    rows = by_workspace("opportunities", wid)
    out = []
    for o in rows:
        c = get_by_id("companies", o.get("company_id") or "")
        name = (c or {}).get("name")
        out.append({**o, "company_name": name, "company": o.get("company") or name})
    return out


@app.get("/api/v1/opportunities/{oid}")
def get_opp(oid: str, wid: str = Depends(workspace_id)):
    o = get_by_id("opportunities", oid)
    if not o:
        o = next((item for item in by_workspace("opportunities", wid) if item.get("id", "").startswith(oid)), None)
    if not o:
        from app.sources import _load_catalog

        for item in _load_catalog():
            if item.get("id") == oid:
                o = {
                    "id": oid,
                    "workspace_id": wid,
                    "title": item.get("title") or "Discovered Opportunity",
                    "requirement": item.get("requirement") or item.get("description") or "Not detected",
                    "company": item.get("company"),
                    "company_name": item.get("company"),
                    "source": item.get("source") or "Public Web",
                    "source_url": item.get("source_url"),
                    "published_at": item.get("published_at"),
                    "detected_at": utcnow(),
                    "location": item.get("location") or "Not detected",
                    "industry": item.get("industry") or "Not detected",
                    "confidence": item.get("confidence") or 0.85,
                    "score": {
                        "label": "AI Opportunity Score",
                        "total": int(round((item.get("confidence") or 0.85) * 100)),
                        "service_match": 85,
                        "intent_score": 85,
                        "freshness_score": 90,
                        "technology_match": 85,
                        "company_fit": 80,
                    },
                    "label": item.get("label") or "VERIFIED SIGNAL",
                    "is_demo": False,
                    "status": "new",
                }
                create_record("opportunities", o, ignore_duplicate=True)
                break
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
    nbas = get_ai().next_best_action(quals[-1] if quals else None, o)
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
        "is_demo": bool(o.get("is_demo")),
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
    from app.intel import refresh_opportunity_intel

    market = refresh_opportunity_intel(o, refresh=False)
    analysis = get_ai().analyze_opportunity(profiles[0], o, signals, market)
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
            "source_mode": analysis.get("source_mode"),
            "analyzed_at": utcnow(),
        },
    )
    if o.get("lead_id"):
        update_record("leads", o["lead_id"], {"opportunity_score": analysis["total"], "last_updated": utcnow()})
    audit(wid, user["id"], "analyze_opportunity", "opportunity", oid)
    return {"opportunity": updated, "analysis": analysis, "evidence": analysis["evidence"]}


@app.post("/api/v1/opportunities/{oid}/add-lead")
def add_lead_from_opp(oid: str, wid: str = Depends(workspace_id), user=Depends(current_user)):
    o = get_by_id("opportunities", oid)
    if not o or o.get("workspace_id") != wid:
        raise HTTPException(404, "Opportunity not found")
    # If already linked to a lead, return existing
    if o.get("lead_id"):
        existing = get_by_id("leads", o["lead_id"])
        if existing:
            return {"lead": existing, "created": False, "message": "Lead already exists for this opportunity"}
    # Build lead from opportunity data
    company_name = o.get("company_name") or o.get("company") or o.get("title") or "Unknown Company"
    company_record = get_by_id("companies", o.get("company_id") or "")
    contact_record = get_by_id("contacts", o.get("contact_id") or "") if o.get("contact_id") else None
    lead_id = new_id("lead")
    lead = create_record(
        "leads",
        {
            "id": lead_id,
            "workspace_id": wid,
            "name": (contact_record or {}).get("name") or company_name,
            "company": company_name,
            "email": _resolve_lead_email((contact_record or {}).get("email")),
            "phone": (contact_record or {}).get("phone") or "",
            "job_title": (contact_record or {}).get("title") or "",
            "website": o.get("source_url") or (company_record or {}).get("website") or "",
            "location": o.get("location") or (company_record or {}).get("location") or "",
            "industry": o.get("industry") or (company_record or {}).get("industry") or "",
            "notes": f"Auto-created from Opportunity: {o.get('title') or o.get('requirement') or ''}. Source: {o.get('source') or 'Opportunity Discovery'}",
            "pipeline_stage": "New",
            "intent_level": "Unknown",
            "opportunity_id": oid,
            "opportunity_score": (o.get("score") or {}).get("total"),
            "source": o.get("source") or "Opportunity Discovery",
            "created_at": utcnow(),
            "last_updated": utcnow(),
        },
    )
    # Link lead back to opportunity
    update_record("opportunities", oid, {"lead_id": lead_id, "status": "lead_created"})
    audit(wid, user["id"], "add_lead_from_opportunity", "lead", lead_id, {"opportunity_id": oid})
    return {"lead": lead, "created": True, "message": f"Lead created from opportunity: {company_name}"}


@app.get("/api/v1/buying-signals")
def list_signals(wid: str = Depends(workspace_id)):
    return by_workspace("buying_signals", wid)


@app.get("/api/v1/opportunities/{oid}/market-intelligence")
def market(oid: str, refresh: bool = False, wid: str = Depends(workspace_id)):
    o = get_by_id("opportunities", oid)
    if not o or o.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    if refresh:
        from app.intel import refresh_opportunity_intel

        refresh_opportunity_intel(o, refresh=True)
    rows = [m for m in by_workspace("market_signals", wid) if m.get("opportunity_id") == oid]
    out = []
    for m in rows:
        out.append(
            {
                **m,
                "signal_type": m.get("signal_type") or m.get("kind"),
                "source_name": m.get("source_name") or m.get("source"),
                "retrieved_at": m.get("retrieved_at") or m.get("last_updated"),
                "observed_at": m.get("observed_at") or m.get("last_updated"),
                "status": m.get("status") or ("observed" if m.get("detected") else "not_detected"),
            }
        )
    return out


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
    return {"company": company, "contact": contact, "is_demo": bool((company or {}).get("is_demo") if company else o.get("is_demo"))}


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


@app.get("/api/v1/leads/export")
def export_leads(
    wid: str = Depends(workspace_id),
    format: str = "csv",
    q: str | None = None,
    ids: str | None = None,
    segment_id: str | None = None,
):
    rows = by_workspace("leads", wid)
    if ids:
        wanted = set(ids.split(","))
        rows = [r for r in rows if r.get("id") in wanted]
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in " ".join(str(r.get(k) or "") for k in ("name", "company", "email", "notes")).lower()]
    if segment_id:
        seg = get_by_id("lead_segments", segment_id)
        if not seg or seg.get("workspace_id") != wid:
            raise HTTPException(404, "Segment not found")
        rows = apply_segment(rows, seg)
    flat = [flatten_lead(l, get_by_id("companies", l.get("company_id") or "") if l.get("company_id") else None) for l in rows]
    if format == "xlsx":
        return Response(
            to_xlsx(flat),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=leads.xlsx"},
        )
    return Response(to_csv(flat), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=leads.csv"})


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
    tasks = [t for t in by_workspace("tasks", wid) if t.get("lead_id") == lid]
    campaigns = [c for c in by_workspace("campaigns", wid) if lid in (c.get("lead_ids") or [])]
    notes_timeline = [
        {"type": "created", "at": lead.get("created_at"), "text": "Lead created"},
        *[{"type": "call", "at": c.get("started_at"), "text": f"Call {c.get('outcome')}"} for c in calls],
        *[{"type": "task", "at": t.get("created_at"), "text": t.get("title")} for t in tasks],
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
    return {
        "lead": lead,
        "company": company,
        "contact": contact,
        "opportunity": opp,
        "calls": calls,
        "qualifications": quals,
        "tasks": tasks,
        "campaigns": campaigns,
        "timeline": notes_timeline,
        "enrichment": enrichment,
    }


@app.post("/api/v1/leads")
def create_lead(body: LeadIn, wid: str = Depends(workspace_id), user=Depends(current_user)):
    payload = dict(body.model_dump())
    payload["email"] = _resolve_lead_email(payload.get("email"))
    rec = create_record(
        "leads",
        {
            "id": new_id("lead"),
            "workspace_id": wid,
            **payload,
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
    payload = client_patch(payload)
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
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".csv", ".xlsx", ".txt"):
        raise HTTPException(400, "Only CSV or XLSX allowed")
    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(400, "File too large")
    rows = _parse_table(content, file.filename or "file.csv")
    headers = list(rows[0].keys()) if rows else []
    mapping = {}
    for field, aliases in FIELD_ALIASES.items():
        for h in headers:
            if h in aliases:
                mapping[field] = h
                break
    existing_emails = {l.get("email") for l in by_workspace("leads", wid) if l.get("email")}
    report = validate_import_rows(rows, mapping, {e.lower() for e in existing_emails if e})
    preview = []
    for idx, r in enumerate(rows[:50], start=2):
        email = (r.get(mapping.get("email") or "email") or "").strip()
        company = (r.get(mapping.get("company") or "company") or "").strip()
        preview.append(
            {
                "row": r,
                "duplicate": email.lower() in {e.lower() for e in existing_emails if e},
                "valid": bool(company) and (not email or "@" in email),
                "line": idx,
            }
        )
    return {"headers": headers, "mapping": mapping, "preview": preview, "count": len(rows), **report}


class ImportCommit(BaseModel):
    mapping: dict
    rows: list[dict]


@app.post("/api/v1/leads/import")
def import_commit(body: ImportCommit, wid: str = Depends(workspace_id), user=Depends(current_user)):
    existing_emails = {l.get("email") for l in by_workspace("leads", wid) if l.get("email")}
    report = validate_import_rows(body.rows, body.mapping, {e.lower() for e in existing_emails if e})
    created = []
    skipped = []
    for r in report["valid"]:
        mapped = {f: r.get(col) for f, col in body.mapping.items()}
        email = _resolve_lead_email(mapped.get("email"))
        rec = create_record(
            "leads",
            {
                "id": new_id("lead"),
                "workspace_id": wid,
                "name": mapped.get("name"),
                "company": mapped.get("company"),
                "email": email,
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
    skipped = report["errors"]
    audit(wid, user["id"], "import_leads", "lead", None, {"created": len(created)})
    return {"created": created, "skipped": skipped, **{k: report[k] for k in ("total_rows", "valid_rows", "invalid_rows", "duplicate_rows", "errors")}}


@app.get("/api/v1/segments")
def list_segments(wid: str = Depends(workspace_id)):
    segs = segments_repo.by_workspace(wid)
    leads = by_workspace("leads", wid)
    out = []
    for s in segs:
        matched = apply_segment(leads, s)
        out.append({**s, "leads": matched, "count": len(matched)})
    return out


@app.post("/api/v1/segments")
def create_segment(body: SegmentIn, wid: str = Depends(workspace_id), user=Depends(current_user)):
    rec = segments_repo.create(
        {
            "id": new_id("seg"),
            "workspace_id": wid,
            **body.model_dump(),
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
    )
    audit(wid, user["id"], "create_segment", "lead_segment", rec["id"])
    return rec


@app.patch("/api/v1/segments/{sid}")
def patch_segment(sid: str, body: SegmentIn, wid: str = Depends(workspace_id), user=Depends(current_user)):
    s = get_by_id("lead_segments", sid)
    if not s or s.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    rec = update_record("lead_segments", sid, {**body.model_dump(), "updated_at": utcnow()})
    audit(wid, user["id"], "update_segment", "lead_segment", sid)
    return rec


@app.delete("/api/v1/segments/{sid}")
def delete_segment(sid: str, wid: str = Depends(workspace_id), user=Depends(current_user)):
    s = get_by_id("lead_segments", sid)
    if not s or s.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    delete_record("lead_segments", sid)
    audit(wid, user["id"], "delete_segment", "lead_segment", sid)
    return {"ok": True}


@app.post("/api/v1/segments/preview")
def preview_segment(body: SegmentIn, wid: str = Depends(workspace_id)):
    leads = by_workspace("leads", wid)
    matched = apply_segment(leads, body.model_dump())
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
    ws = get_by_id("workspaces", wid) or {}
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
    if ws.get("mode") == "live" and bolna_client.is_configured():
        try:
            bid = live_voice.sync_agent(rec)
            rec = update_record("voice_agents", rec["id"], {"bolna_agent_id": bid})
        except bolna_client.BolnaError as e:
            log.warning("Bolna create_agent failed for %s: %s", rec["id"], e)
            rec = update_record("voice_agents", rec["id"], {"bolna_sync_error": str(e)})
    return rec


@app.patch("/api/v1/voice-agents/{aid}")
def patch_agent(aid: str, payload: dict, wid: str = Depends(workspace_id)):
    a = get_by_id("voice_agents", aid)
    if not a or a.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    ws = get_by_id("workspaces", wid) or {}
    updated = update_record("voice_agents", aid, client_patch(payload))
    if ws.get("mode") == "live" and bolna_client.is_configured() and updated.get("bolna_agent_id"):
        try:
            live_voice.sync_agent(updated)
            updated.pop("bolna_sync_error", None)
            updated = update_record("voice_agents", aid, {"bolna_sync_error": None})
        except bolna_client.BolnaError as e:
            log.warning("Bolna patch_agent failed for %s: %s", aid, e)
            updated = update_record("voice_agents", aid, {"bolna_sync_error": str(e)})
    return updated


@app.delete("/api/v1/voice-agents/{aid}")
def delete_agent(aid: str, wid: str = Depends(workspace_id)):
    a = get_by_id("voice_agents", aid)
    if not a or a.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    if bolna_client.is_configured() and a.get("bolna_agent_id"):
        try:
            live_voice.delete_agent(a)
        except bolna_client.BolnaError as e:
            log.warning("Bolna delete_agent failed for %s: %s", aid, e)
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
    if result.get("escalated"):
        from app.calendly_service import DEFAULT_CALENDLY_URL, PREFERRED_TIMESLOTS
        result["calendly_sms"] = {
            "sent": True,
            "calendly_link": f"{DEFAULT_CALENDLY_URL}?demo=1",
            "body": f"Hi! Here is the link to schedule your call with Northwind Digital's team: {DEFAULT_CALENDLY_URL}?demo=1 — select your preferred timeslot whenever you're ready!",
            "preferred_slots": PREFERRED_TIMESLOTS,
        }
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


@app.patch("/api/v1/campaigns/{cid}")
def patch_campaign(cid: str, payload: dict, wid: str = Depends(workspace_id), user=Depends(current_user)):
    c = get_by_id("campaigns", cid)
    if not c or c.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    allowed = {"name", "objective", "lead_ids", "qualification_questions", "language", "schedule", "scheduled_at", "quiet_hours", "retry_policy", "agent_id"}
    patch = {k: v for k, v in client_patch(payload).items() if k in allowed}
    if "lead_ids" in patch and not isinstance(patch["lead_ids"], list):
        raise HTTPException(400, "lead_ids must be a list")
    updated = update_record("campaigns", cid, patch)
    audit(wid, user["id"], "patch_campaign", "campaign", cid, {"fields": list(patch.keys())})
    return updated


@app.post("/api/v1/campaigns")
def create_campaign(body: CampaignIn, wid: str = Depends(workspace_id), user=Depends(current_user)):
    rec = create_record(
        "campaigns",
        {
            "id": new_id("camp"),
            "workspace_id": wid,
            **body.model_dump(),
            "retry_policy": body.retry_policy
            or {"max_attempts": 3, "interval_minutes": 60, "on": ["No Answer", "Voicemail"], "sequence": ["No Answer", "Voicemail", "Interested"]},
            "quiet_hours": body.quiet_hours or {"start": "21:00", "end": "08:00"},
            "lead_attempts": {},
            "timeline": [],
            "label": "DEMO CAMPAIGN SIMULATION",
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
        if not bolna_client.is_configured():
            raise HTTPException(400, "BOLNA_API_KEY is not configured on the server.")
        agent = get_by_id("voice_agents", c.get("agent_id"))
        if not agent or agent.get("workspace_id") != wid:
            raise HTTPException(400, "Live campaigns require a valid voice agent.")
        if not agent.get("bolna_agent_id"):
            try:
                bid = live_voice.sync_agent(agent)
                agent = update_record("voice_agents", agent["id"], {"bolna_agent_id": bid})
            except bolna_client.BolnaError as e:
                raise HTTPException(502, f"Bolna agent sync failed: {e}")
    status = "running" if c.get("schedule") == "immediate" else "scheduled"
    updated = update_record("campaigns", cid, {"status": status, "launched_at": utcnow(), "mode": mode})
    audit(wid, user["id"], "launch_campaign", "campaign", cid)
    return updated


@app.post("/api/v1/campaigns/{cid}/pause")
def pause_campaign(cid: str, wid: str = Depends(workspace_id), user=Depends(current_user)):
    rec = update_record("campaigns", cid, {"status": "paused"})
    audit(wid, user["id"], "pause_campaign", "campaign", cid)
    return rec


@app.post("/api/v1/campaigns/{cid}/resume")
def resume_campaign(cid: str, wid: str = Depends(workspace_id), user=Depends(current_user)):
    rec = update_record("campaigns", cid, {"status": "running"})
    audit(wid, user["id"], "resume_campaign", "campaign", cid)
    return rec


class SimulateCallIn(BaseModel):
    lead_id: str
    prospect_script: str | None = None
    outcome_hint: str | None = None
    language: str = "en"


HINT_SCRIPTS = {
    "No Answer": "no answer",
    "Voicemail": "",
    "Connected": "connected",
    "Callback Requested": "I want a callback.",
    "Not Interested": "I am not interested. Do not call again.",
    "Interested": "We are looking for SharePoint migration support and want to start this month.",
    "Escalated": "Please transfer me to a real person.",
    "Human Handoff": "Please transfer me to a real person.",
    "Calendly Recall": "Hi, I have not booked a timeslot yet.",
}


@app.post("/api/v1/campaigns/{cid}/next-step")
def campaign_next_step(cid: str, lead_id: str, force: bool = False, language: str = "en", wid: str = Depends(workspace_id), user=Depends(current_user)):
    campaign = get_by_id("campaigns", cid)
    if not campaign or campaign.get("workspace_id") != wid:
        raise HTTPException(404, "Campaign not found")
    plan = next_step_plan(campaign, lead_id, force=force)
    if not plan.get("eligible"):
        return {**plan, "campaign": campaign}
    body = SimulateCallIn(lead_id=lead_id, outcome_hint=plan["planned_outcome"], language=language)
    result = simulate_call(cid, body, wid, user)
    attempts = dict(campaign.get("lead_attempts") or {})
    row = dict(attempts.get(lead_id) or {"count": 0, "timeline": []})
    row["count"] = int(row.get("count") or 0) + 1
    row.setdefault("timeline", []).append(
        {
            "attempt": row["count"],
            "outcome": result["call"]["outcome"],
            "at": utcnow(),
            "retry_scheduled": bool(plan.get("retry_eligible")),
        }
    )
    attempts[lead_id] = row
    timeline = list(campaign.get("timeline") or [])
    timeline.append({"lead_id": lead_id, **row["timeline"][-1]})
    updated = update_record("campaigns", cid, {"lead_attempts": attempts, "timeline": timeline, "status": "running"})
    audit(wid, user["id"], "campaign_next_step", "campaign", cid, {"lead_id": lead_id, "outcome": result["call"]["outcome"]})
    return {**plan, "result": result, "campaign": updated, "label": "DEMO CAMPAIGN SIMULATION"}


@app.post("/api/v1/campaigns/{cid}/calls/simulate")
def simulate_call(cid: str, body: SimulateCallIn, wid: str = Depends(workspace_id), user=Depends(current_user)):
    campaign = get_by_id("campaigns", cid)
    if not campaign or campaign.get("workspace_id") != wid:
        raise HTTPException(404, "Campaign not found")
    lead = get_by_id("leads", body.lead_id)
    if not lead or lead.get("workspace_id") != wid:
        raise HTTPException(404, "Lead not found")

    ws = get_by_id("workspaces", wid) or {}
    if (ws.get("mode") or "demo") == "live":
        return _dispatch_live_call(campaign, lead, body, wid, user)
    if lead.get("phone") or lead.get("email"):
        blocked = any(
            (lead.get("phone") and o.get("phone") == lead.get("phone"))
            or (lead.get("email") and o.get("email") == lead.get("email"))
            for o in by_workspace("opt_outs", wid)
        )
        if blocked:
            raise HTTPException(400, "Lead is on the do-not-contact list")
    agent = get_by_id("voice_agents", campaign.get("agent_id"))
    if not agent or agent.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    hint = body.outcome_hint or "Interested"
    script = body.prospect_script if body.prospect_script is not None else HINT_SCRIPTS.get(hint, HINT_SCRIPTS["Interested"])
    loc = body.language or campaign.get("language") or "en"
    if loc == "auto":
        lead_loc = (lead.get("location") or "").lower()
        if any(w in lead_loc for w in ["india", "delhi", "mumbai", "bangalore", "noida", "gurgaon", "hyderabad", "pune"]):
            loc = "hi"
        elif any(w in lead_loc for w in ["gujarat", "ahmedabad", "surat", "vadodara", "rajkot"]):
            loc = "gu"
        elif any(w in lead_loc for w in ["spain", "mexico", "madrid", "barcelona", "argentina", "colombia"]):
            loc = "es"
        elif any(w in lead_loc for w in ["france", "paris", "lyon", "quebec", "belgium"]):
            loc = "fr"
        elif any(w in lead_loc for w in ["germany", "berlin", "munich", "austria", "switzerland", "frankfurt"]):
            loc = "de"
        else:
            loc = "en"
    history = [{"speaker": "agent", "text": opening_message(agent, loc), "ts": utcnow()}]
    if hint == "No Answer" or script.lower().strip() == "no answer":
        result = agent_reply(agent, "no answer", history, loc)
        result["outcome"] = "No Answer"
        result["qualification"]["interest_level"] = "Unknown"
        result["qualification"]["high_intent"] = False
    elif hint == "Voicemail" or script.strip() == "":
        result = agent_reply(agent, "voicemail", history, loc)
        result["outcome"] = "Voicemail"
        result["qualification"]["interest_level"] = "Unknown"
        result["qualification"]["high_intent"] = False
    elif hint in ("Escalated", "Human Handoff"):
        result = agent_reply(agent, "Please transfer me to a real person.", history, loc)
        result["outcome"] = "Escalated"
    elif hint == "Calendly Recall":
        result = agent_reply(agent, "calendly recall", history, loc)
        result["outcome"] = "Connected"
    elif hint == "Connected":
        result = agent_reply(agent, "connected", history, loc)
        result["outcome"] = "Connected"
    else:
        result = agent_reply(agent, script, history, loc)
    outcome = result.get("outcome") or hint or "Connected"
    duration = 0 if outcome == "No Answer" else (8 if outcome == "Voicemail" else 42)
    is_escalated = bool(result.get("escalated") or outcome == "Escalated" or hint in ("Escalated", "Human Handoff"))
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
            "duration_sec": duration,
            "language": loc,
            "stop_reason": result.get("stop_reason") or ("no_answer" if outcome == "No Answer" else None),
            "escalated": is_escalated,
            "escalated_at": utcnow() if is_escalated else None,
            "handoff_reason": "Prospect requested a human specialist" if is_escalated else None,
            "voicemail_message": (agent.get("approved_voicemail") or scripts(loc)["voicemail"]) if outcome == "Voicemail" else None,
            "voicemail_status": "left" if outcome == "Voicemail" else None,
            "callback_requested": outcome == "Callback Requested",
            "retry_eligible": outcome in ("No Answer", "Voicemail"),
            "is_recall": hint == "Calendly Recall",
            "recall_reason": "unbooked_calendly_link" if hint == "Calendly Recall" else None,
            "started_at": utcnow(),
            "is_demo": True,
        },
    )
    sms_result = None
    if is_escalated:
        # Auto-detect explicit callback time from the conversation. If the
        # prospect named a time ("tomorrow at 11 am"), schedule via Calendly
        # API (fires confirmation email) instead of sending a generic SMS link.
        from app.voice import parse_callback_request
        demo_prospect_text = " ".join(
            (t.get("text") or "") for t in (result.get("history") or [])
            if (t.get("speaker") or "") == "prospect"
        ) or (script or "")
        demo_parsed = parse_callback_request(demo_prospect_text) if demo_prospect_text else None
        if demo_parsed:
            from app.calendly_service import schedule_callback
            sms_result = schedule_callback(
                workspace_id=wid,
                lead_id=lead["id"],
                parsed=demo_parsed,
                call_id=call["id"],
                campaign_id=cid,
                raw_user_text=demo_prospect_text,
            )
        else:
            from app.calendly_service import send_calendly_sms
            sms_result = send_calendly_sms(
                workspace_id=wid,
                lead_id=lead["id"],
                call_id=call["id"],
                campaign_id=cid,
                to_phone=lead.get("phone"),
            )
        call = get_by_id("calls", call["id"]) or call
    transcript = None
    nba = get_ai().next_best_action(result["qualification"], get_by_id("opportunities", lead.get("opportunity_id") or ""))
    if outcome != "No Answer":
        transcript = create_record(
            "transcripts",
            {
                "id": new_id("tr"),
                "workspace_id": wid,
                "call_id": call["id"],
                "turns": result["history"],
                "summary": _summarize(result, lead),
                "requirements": result["qualification"].get("requirements"),
                "objections": "Internal IT team" if "internal" in (script or "").lower() else None,
                "interest_level": result["qualification"].get("interest_level"),
                "recommended_action": nba,
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
    qual_status = lead.get("qualification_status") or "not_started"
    if result["qualification"].get("high_intent"):
        stage = "qualified"
        intent_store = "interested"
        qual_status = "complete"
    elif intent == "Not Interested":
        stage = "lost"
        intent_store = "Not Interested"
        qual_status = "complete"
        create_record("opt_outs", {"id": new_id("opt"), "workspace_id": wid, "phone": lead.get("phone"), "email": lead.get("email"), "reason": "not_interested", "created_at": utcnow()})
    elif outcome == "No Answer":
        stage = lead.get("pipeline_stage") or "contacted"
        intent_store = lead.get("intent_level") or "unknown"
        qual_status = lead.get("qualification_status") or "not_started"
    elif intent == "Callback" or outcome == "Escalated":
        stage = "contacted"
        intent_store = "Callback"
        qual_status = "in_progress"
    else:
        stage = "contacted"
        intent_store = intent
        qual_status = "in_progress" if outcome != "Interested" else "complete"
    update_record(
        "leads",
        lead["id"],
        {
            "pipeline_stage": stage,
            "intent_level": intent_store,
            "qualification_status": qual_status,
            "last_updated": utcnow(),
            "campaign_ids": list(set((lead.get("campaign_ids") or []) + [cid])),
        },
    )
    task = None
    create_task = result["qualification"].get("high_intent") or result.get("escalated") or intent == "Callback" or outcome in ("Callback Requested", "Escalated", "Interested")
    if create_task and outcome != "Not Interested":
        due = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()
        task = create_record(
            "tasks",
            {
                "id": new_id("task"),
                "workspace_id": wid,
                "title": f"Follow up with {lead.get('company')}",
                "priority": "HIGH",
                "due": due,
                "reason": (result["qualification"].get("banner_reason") or script or outcome)[:200],
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
        "next_best_action": nba,
        "agent_turns": result["history"],
        "retry_eligible": outcome in ("No Answer", "Voicemail"),
        "sms": sms_result.get("sms") if sms_result else None,
        "calendly_booking": sms_result.get("booking") if sms_result else None,
        "calendly_link": sms_result.get("calendly_link") if sms_result else None,
    }


# ---------------- Bolna live dispatch + webhook reconcile ----------------

def _dispatch_live_call(campaign: dict, lead: dict, body: SimulateCallIn, wid: str, user: dict) -> dict:
    if not bolna_client.is_configured():
        raise HTTPException(400, "BOLNA_API_KEY is not configured on the server.")
    if lead.get("phone") or lead.get("email"):
        blocked = any(
            (lead.get("phone") and o.get("phone") == lead.get("phone"))
            or (lead.get("email") and o.get("email") == lead.get("email"))
            for o in by_workspace("opt_outs", wid)
        )
        if blocked:
            raise HTTPException(400, "Lead is on the do-not-contact list")
    agent = get_by_id("voice_agents", campaign.get("agent_id"))
    if not agent or agent.get("workspace_id") != wid:
        raise HTTPException(404, "Voice agent not found")
    if not agent.get("bolna_agent_id"):
        try:
            bid = live_voice.sync_agent(agent)
            agent = update_record("voice_agents", agent["id"], {"bolna_agent_id": bid})
        except bolna_client.BolnaError as e:
            raise HTTPException(502, f"Bolna agent sync failed: {e}")
    recipient = (lead.get("phone") or "").strip()
    if not recipient:
        raise HTTPException(400, "Lead has no phone number")
    ws = get_by_id("workspaces", wid) or {}
    from_phone = ws.get("from_phone_number") or settings.bolna_from_phone
    try:
        resp = live_voice.dispatch(
            agent=agent,
            recipient_phone=recipient,
            lead=lead,
            from_phone=from_phone,
            language=body.language or campaign.get("language") or "auto",
        )
    except bolna_client.BolnaError as e:
        raise HTTPException(502, f"Bolna dispatch failed: {e}")
    execution_id = (resp or {}).get("execution_id") or (resp or {}).get("data", {}).get("execution_id")
    if not execution_id:
        raise HTTPException(502, f"Bolna dispatch returned no execution_id: {resp!r}")
    call = create_record(
        "calls",
        {
            "id": new_id("call"),
            "workspace_id": wid,
            "campaign_id": campaign["id"],
            "lead_id": lead["id"],
            "opportunity_id": lead.get("opportunity_id"),
            "agent_id": agent["id"],
            "mode": "live",
            "label": "Live Bolna Call",
            "outcome": "Queued",
            "duration_sec": 0,
            "language": body.language or campaign.get("language") or "en",
            "status": (resp or {}).get("status") or "queued",
            "bolna_execution_id": execution_id,
            "bolna_response": resp,
            "started_at": utcnow(),
            "is_demo": False,
            "retry_eligible": False,
        },
    )
    audit(wid, user["id"], "dispatch_call", "call", call["id"], {"execution_id": execution_id})
    return {
        "label": "Live Bolna Call",
        "call": call,
        "transcript": None,
        "qualification": None,
        "task": None,
        "next_best_action": None,
        "agent_turns": [],
        "retry_eligible": False,
        "execution_id": execution_id,
    }


def _process_bolna_execution(payload: dict) -> dict | None:
    execution_id = payload.get("execution_id") or payload.get("id")
    if not execution_id:
        return None
    call = None
    for c in get_all("calls"):
        if c.get("bolna_execution_id") == execution_id:
            call = c
            break
    if not call:
        log.info("Bolna execution %s has no matching call record", execution_id)
        return None
    wid = call["workspace_id"]
    lead = get_by_id("leads", call.get("lead_id")) or {}
    updates: dict = {"status": payload.get("status") or call.get("status")}
    duration = payload.get("conversation_time") or payload.get("total_duration") or 0
    if duration:
        try:
            updates["duration_sec"] = int(float(duration))
        except Exception:
            pass
    outcome = bolna_client.extract_outcome(payload)
    updates["outcome"] = outcome
    if payload.get("recording_url"):
        updates["recording_url"] = payload.get("recording_url")
    transcript_turns = bolna_client.extract_transcript_turns(payload)
    transcript = None
    qualification = None
    task = None
    if transcript_turns:
        transcript = next((t for t in by_workspace("transcripts", wid) if t.get("call_id") == call["id"]), None)
        transcript_payload = {
            "turns": transcript_turns,
            "summary": (payload.get("summary") or ""),
            "interest_level": payload.get("extracted_data", {}).get("interest_level") if isinstance(payload.get("extracted_data"), dict) else None,
            "source": "bolna",
        }
        if transcript:
            transcript = update_record("transcripts", transcript["id"], transcript_payload)
        else:
            transcript = create_record(
                "transcripts",
                {
                    "id": new_id("tr"),
                    "workspace_id": wid,
                    "call_id": call["id"],
                    **transcript_payload,
                    "is_demo": False,
                },
            )
    extracted = payload.get("extracted_data") if isinstance(payload.get("extracted_data"), dict) else {}
    intent = (extracted.get("interest_level") or "").lower()
    if intent in ("interested", "high_intent"):
        high_intent = True
        interest_level = "Interested"
    elif intent in ("not_interested", "opted_out"):
        high_intent = False
        interest_level = "Not Interested"
    elif outcome == "Voicemail":
        high_intent = False
        interest_level = "Unknown"
    else:
        high_intent = bool(extracted.get("high_intent"))
        interest_level = (
            "Interested" if high_intent
            else "Callback" if outcome == "Callback Requested"
            else "Not Interested" if outcome == "Not Interested"
            else "Unknown"
        )
    qual_payload = {
        "interest_level": interest_level,
        "requirements": extracted.get("requirements"),
        "timeline": extracted.get("timeline"),
        "budget": extracted.get("budget"),
        "technology": extracted.get("technology"),
        "decision_stage": extracted.get("decision_stage"),
        "high_intent": high_intent,
        "evidence": extracted.get("evidence") or [],
        "missing_information": extracted.get("missing_information") or [],
    }
    qualification = next((q for q in by_workspace("qualifications", wid) if q.get("call_id") == call["id"]), None)
    if qualification:
        qualification = update_record("qualifications", qualification["id"], qual_payload)
    else:
        qualification = create_record(
            "qualifications",
            {
                "id": new_id("qual"),
                "workspace_id": wid,
                "call_id": call["id"],
                "lead_id": call.get("lead_id"),
                "opportunity_id": call.get("opportunity_id"),
                **qual_payload,
                "is_demo": False,
                "created_at": utcnow(),
            },
        )
    if lead:
        stage_map = {
            "Interested": "qualified",
            "Not Interested": "lost",
            "Callback": "contacted",
            "Unknown": "contacted",
        }
        update_record("leads", lead["id"], {
            "pipeline_stage": stage_map.get(interest_level, "contacted"),
            "intent_level": interest_level,
            "qualification_status": "complete" if interest_level in ("Interested", "Not Interested") else "in_progress",
            "last_updated": utcnow(),
        })
    if high_intent and outcome != "Not Interested":
        due = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()
        existing_tasks = [t for t in by_workspace("tasks", wid) if t.get("call_id") == call["id"]]
        if not existing_tasks:
            task = create_record(
                "tasks",
                {
                    "id": new_id("task"),
                    "workspace_id": wid,
                    "title": f"Follow up with {lead.get('company') or lead.get('name') or 'prospect'}",
                    "priority": "HIGH",
                    "due": due,
                    "reason": extracted.get("banner_reason") or "Bolna call flagged high intent",
                    "status": "open",
                    "lead_id": call.get("lead_id"),
                    "opportunity_id": call.get("opportunity_id"),
                    "call_id": call["id"],
                    "source": "bolna",
                    "is_demo": False,
                    "created_at": utcnow(),
                },
            )
            create_record(
                "notifications",
                {
                    "id": new_id("ntf"),
                    "workspace_id": wid,
                    "type": "high_intent",
                    "title": "HIGH INTENT PROSPECT",
                    "body": task["reason"],
                    "opportunity_id": call.get("opportunity_id"),
                    "read": False,
                    "is_demo": False,
                    "created_at": utcnow(),
                },
            )
    if interest_level == "Not Interested" and lead:
        create_record(
            "opt_outs",
            {
                "id": new_id("opt"),
                "workspace_id": wid,
                "phone": lead.get("phone"),
                "email": lead.get("email"),
                "reason": "not_interested",
                "created_at": utcnow(),
            },
        )

    # Detect explicit callback time in the transcript and schedule a Calendly booking.
    # This overrides the generic opt-out above: a prospect who said "call me tomorrow at 11 am"
    # is not opting out — they want a scheduled callback.
    prospect_text = " ".join(
        t.get("text", "") for t in (transcript_turns or []) if t.get("speaker") == "prospect"
    )
    from app.voice import parse_callback_request
    parsed_time = parse_callback_request(prospect_text) if prospect_text else None
    callback_result = None
    if parsed_time and lead and interest_level != "Not Interested":
        from app.calendly_service import schedule_callback
        callback_result = schedule_callback(
            workspace_id=wid,
            lead_id=lead["id"],
            parsed=parsed_time,
            call_id=call["id"],
            campaign_id=call.get("campaign_id"),
            raw_user_text=prospect_text,
        )
        updates["outcome"] = "Callback Scheduled"
        updates["requested_slot"] = parsed_time
        # Roll back any opt-out row that was just created for this lead.
        from app.store import filter_records as _fr, delete_record as _dr
        for oo in _fr("opt_outs", lambda r: r.get("workspace_id") == wid and (
            (lead.get("phone") and r.get("phone") == lead.get("phone"))
            or (lead.get("email") and r.get("email") == lead.get("email"))
        )):
            _dr("opt_outs", oo["id"])
        update_record("leads", lead["id"], {
            "pipeline_stage": "callback_scheduled",
            "intent_level": "Interested",
            "qualification_status": "in_progress",
            "last_updated": utcnow(),
        })

    update_record("calls", call["id"], updates)
    _bump_analytics(wid, outcome, call.get("duration_sec") or 0)
    final_outcome = updates.get("outcome") or outcome
    return {
        "call_id": call["id"],
        "outcome": final_outcome,
        "callback_scheduled": bool(callback_result),
        "delivery_channel": (callback_result or {}).get("delivery_channel") if isinstance(callback_result, dict) else None,
        "calendly_event_uri": (callback_result or {}).get("calendly_event_uri") if isinstance(callback_result, dict) else None,
        "transcript_id": transcript["id"] if transcript else None,
        "qualification_id": qualification["id"],
        "task_id": task["id"] if task else None,
    }


@app.post("/api/v1/bolna/webhook")
async def bolna_webhook(request: Request):
    raw = await request.body()
    try:
        payload = json.loads(raw) if raw else {}
    except Exception:
        log.warning("Bolna webhook: non-JSON payload (%d bytes)", len(raw))
        raise HTTPException(400, "Invalid JSON")
    result = _process_bolna_execution(payload)
    return {"ok": True, "processed": bool(result), **({"details": result} if result else {})}


@app.get("/api/v1/bolna/health")
def bolna_health(user=Depends(current_user)):
    return live_voice.health()


@app.post("/api/v1/calls/{call_id}/reconcile")
def reconcile_call(call_id: str, wid: str = Depends(workspace_id)):
    call = get_by_id("calls", call_id)
    if not call or call.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    eid = call.get("bolna_execution_id")
    if not eid:
        raise HTTPException(400, "Call has no bolna execution id")
    if not bolna_client.is_configured():
        raise HTTPException(400, "Bolna not configured")
    try:
        payload = bolna_client.get_execution(eid)
    except bolna_client.BolnaError as e:
        raise HTTPException(502, f"Bolna fetch failed: {e}")
    result = _process_bolna_execution(payload)
    return {"execution": payload, "processed": result}


def _summarize(result: dict, lead: dict) -> str:
    q = result.get("qualification") or {}
    return (
        f"Automated qualification call with {lead.get('company')}. Interest: {q.get('interest_level')}. "
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
    elif outcome == "No Answer":
        row["no_answer"] = row.get("no_answer", 0) + 1
    else:
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

    # If the transcript already contains a specific callback time, schedule that
    # instead of sending a generic Calendly link.
    transcript = next((t for t in by_workspace("transcripts", wid) if t.get("call_id") == call_id), None)
    prospect_text = ""
    if transcript:
        prospect_text = " ".join(
            (t.get("text") or "") for t in (transcript.get("turns") or []) if t.get("speaker") == "prospect"
        )
    from app.voice import parse_callback_request
    parsed = parse_callback_request(prospect_text) if prospect_text else None

    sms_res = None
    if lead and parsed:
        from app.calendly_service import schedule_callback
        sms_res = schedule_callback(
            workspace_id=wid,
            lead_id=lead["id"],
            parsed=parsed,
            call_id=call_id,
            campaign_id=c.get("campaign_id"),
            raw_user_text=prospect_text,
        )
    elif lead:
        from app.calendly_service import send_calendly_sms
        sms_res = send_calendly_sms(wid, lead["id"], call_id=call_id, campaign_id=c.get("campaign_id"), to_phone=lead.get("phone"))

    task = create_record(
        "tasks",
        {
            "id": new_id("task"),
            "workspace_id": wid,
            "title": f"Human handoff: {lead.get('company') if lead else 'prospect'}",
            "priority": "HIGH",
            "due": (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat(),
            "reason": (f"Scheduled callback at {parsed['label']}. Calendly confirmation texted." if parsed
                       else "Immediate human handoff requested. Calendly link texted to prospect."),
            "status": "open",
            "assignee": user.get("name"),
            "lead_id": c.get("lead_id"),
            "created_at": utcnow(),
            "is_demo": True,
        },
    )
    return {"call": get_by_id("calls", call_id), "task": task, "sms": sms_res, "callback": parsed}


@app.post("/api/v1/calls/{call_id}/opt-out")
def opt_out(call_id: str, wid: str = Depends(workspace_id)):
    c = get_by_id("calls", call_id)
    if not c or c.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    lead = get_by_id("leads", c.get("lead_id"))
    create_record("opt_outs", {"id": new_id("opt"), "workspace_id": wid, "phone": (lead or {}).get("phone"), "reason": "opt_out", "created_at": utcnow()})
    update_record("calls", call_id, {"stop_reason": "opt_out", "outcome": "Not Interested"})
    return {"ok": True}


class CalendlySmsIn(BaseModel):
    lead_id: str
    call_id: str | None = None
    campaign_id: str | None = None
    phone: str | None = None
    custom_link: str | None = None


class CalendlyBookIn(BaseModel):
    booking_id: str | None = None
    lead_id: str | None = None
    slot_id: str | None = None
    slot_title: str | None = None
    specialist: str | None = None
    notes: str | None = ""


class CalendlyRecallIn(BaseModel):
    campaign_id: str | None = None
    lead_id: str | None = None
    force_immediate: bool = True


class CalendlyScheduleCallbackIn(BaseModel):
    lead_id: str
    time_text: str = Field(..., description="Free-form time mention like 'tomorrow at 11 am'")
    call_id: str | None = None
    campaign_id: str | None = None
    specialist: str | None = None


@app.get("/api/v1/calendly/config")
def get_calendly_config(wid: str = Depends(workspace_id)):
    """Returns the current Calendly configuration so the UI always shows correct URLs."""
    from app.calendly_service import DEFAULT_LEAD_EMAIL, _get_calendly_url
    from app.db import meta_get
    booking_url = _get_calendly_url()
    event_type_uri = meta_get("calendly_event_type_uri") or os.getenv("CALENDLY_EVENT_TYPE_URI", "")
    token_set = bool(os.getenv("CALENDLY_ACCESS_TOKEN", ""))
    webhook_secret_set = bool(os.getenv("CALENDLY_WEBHOOK_SECRET", ""))
    return {
        "booking_url": booking_url,
        "event_type_uri": event_type_uri,
        "has_access_token": token_set,
        "has_webhook_secret": webhook_secret_set,
        "default_email": DEFAULT_LEAD_EMAIL,
    }


@app.get("/api/v1/calendly/preferred-slots")
def get_preferred_slots():
    from app.calendly_service import get_preferred_timeslots
    return get_preferred_timeslots()


@app.get("/api/v1/calendly/bookings")
def list_calendly_bookings(wid: str = Depends(workspace_id)):
    return by_workspace("calendly_bookings", wid)


@app.get("/api/v1/calendly/bookings/{bid}")
def get_calendly_booking(bid: str, wid: str = Depends(workspace_id)):
    b = get_by_id("calendly_bookings", bid)
    if not b or b.get("workspace_id") != wid:
        raise HTTPException(404, "Booking not found")
    return b


@app.post("/api/v1/calendly/send-sms")
def api_send_calendly_sms(body: CalendlySmsIn, wid: str = Depends(workspace_id)):
    from app.calendly_service import send_calendly_sms
    return send_calendly_sms(
        workspace_id=wid,
        lead_id=body.lead_id,
        call_id=body.call_id,
        campaign_id=body.campaign_id,
        to_phone=body.phone,
        custom_link=body.custom_link,
    )


@app.post("/api/v1/calendly/book")
def api_book_calendly_slot(body: CalendlyBookIn, wid: str = Depends(workspace_id), user=Depends(current_user)):
    from app.calendly_service import complete_calendly_booking
    return complete_calendly_booking(
        workspace_id=wid,
        booking_id=body.booking_id,
        lead_id=body.lead_id,
        slot_id=body.slot_id,
        slot_title=body.slot_title,
        specialist=body.specialist,
        notes=body.notes or "",
        user_name=user.get("name"),
    )


@app.post("/api/v1/calendly/webhook")
async def calendly_webhook(request: Request):
    """
    Receives Calendly webhook events (invitee.created / invitee.canceled).

    Real Calendly invitee.created payload shape:
    {
      "event": "invitee.created",
      "payload": {
        "event_type": { "name": "Northwind Consultation", "uri": "..." },
        "event": {
          "start_time": "2026-09-26T14:00:00Z",
          "end_time":   "2026-09-26T14:30:00Z",
          "uri": "..."
        },
        "invitee": {
          "name": "John Smith",
          "email": "john@acme.com",
          "uri": "..."
        },
        "tracking": {
          "utm_content": "<booking_ref>",   # we put booking_ref here
          "utm_source":  "<lead_id>"
        },
        "questions_and_answers": [
          { "question": "booking_ref", "answer": "<booking_ref>" }
        ]
      }
    }
    """
    import hmac, hashlib, time
    raw_body = await request.body()

    # Signature verification per https://developer.calendly.com/api-docs/
    # Header format: "t=<unix_ts>,v1=<hex_hmac_sha256>"
    # Signed payload: "<t>.<raw_body>"  (t concatenated with "." + raw bytes)
    # Replay window:  tolerance seconds (default 180s = 3 min, Calendly's example)
    secret = os.getenv("CALENDLY_WEBHOOK_SECRET", "")
    if secret:
        sig_header = request.headers.get("Calendly-Webhook-Signature", "")
        parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
        t_str = parts.get("t", "")
        v1 = parts.get("v1", "")
        if not t_str or not v1:
            raise HTTPException(403, "Invalid webhook signature header")

        tolerance = int(os.getenv("CALENDLY_WEBHOOK_TOLERANCE_SECONDS", "180"))
        try:
            ts = int(t_str)
        except ValueError:
            raise HTTPException(403, "Invalid webhook signature timestamp")
        if abs(int(time.time()) - ts) > tolerance:
            raise HTTPException(403, "Webhook signature outside tolerance window")

        signed_payload = t_str.encode("ascii") + b"." + raw_body
        expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, v1):
            raise HTTPException(403, "Invalid webhook signature")

    try:
        payload = json.loads(raw_body)
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    event = payload.get("event", "")
    data = payload.get("payload") or {}

    # Workspace — prefer header, fall back to default
    wid = request.headers.get("X-Workspace-Id") or "workspace_001"

    if event not in ("invitee.created", "invitee.canceled"):
        # Ignore other events (e.g. routing_form_submission)
        return {"ok": True, "event": event, "action": "ignored"}

    # ── Extract tracking params ──────────────────────────────────────────────
    tracking  = data.get("tracking") or {}
    questions = data.get("questions_and_answers") or []
    q_map     = {q.get("question", "").lower(): q.get("answer", "") for q in questions}

    # booking_ref: look in utm_content first, then questions, then utm_source
    booking_ref = (
        tracking.get("utm_content")
        or q_map.get("booking_ref")
        or q_map.get("booking ref")
        or None
    )
    lead_id = (
        tracking.get("utm_source")
        or q_map.get("lead_id")
        or q_map.get("lead id")
        or None
    )

    # ── Event details ────────────────────────────────────────────────────────
    event_info     = data.get("event") or {}
    event_type     = data.get("event_type") or {}
    invitee        = data.get("invitee") or {}

    slot_title     = event_type.get("name") or "Northwind Digital Consultation"
    start_time     = event_info.get("start_time") or ""
    end_time       = event_info.get("end_time") or ""
    if start_time:
        slot_title = f"{slot_title} — {start_time[:16].replace('T', ' ')} UTC"

    invitee_name   = invitee.get("name") or "Lead"
    invitee_email  = invitee.get("email") or ""

    # Specialist: try assigned_to, fall back to Sarah Jenkins
    assigned_to    = (data.get("assigned_to") or [{}])[0] if data.get("assigned_to") else {}
    specialist     = assigned_to.get("name") if isinstance(assigned_to, dict) else "Sarah Jenkins"
    specialist     = specialist or "Sarah Jenkins"

    from app.calendly_service import complete_calendly_booking

    if event == "invitee.canceled":
        # Mark booking as pending again so it can be re-recalled
        if booking_ref:
            from app.store import update_record as _upd
            _upd("calendly_bookings", booking_ref, {
                "status": "pending_booking",
                "canceled_at": utcnow(),
                "cancellation_reason": data.get("cancellation", {}).get("reason", "Canceled via Calendly"),
            })
        return {"ok": True, "event": event, "action": "reverted_to_pending"}

    # invitee.created → mark as booked
    result = complete_calendly_booking(
        workspace_id=wid,
        booking_id=booking_ref,
        lead_id=lead_id,
        slot_title=slot_title,
        specialist=specialist,
        notes=f"Booked via Calendly webhook. Invitee: {invitee_name} <{invitee_email}>. Start: {start_time}.",
    )
    return {"ok": True, "event": event, "action": "booking_confirmed", "booking_id": booking_ref, **result}


@app.get("/api/v1/calendly/confirm")
def calendly_confirm_redirect(
    booking_ref: str | None = None,
    lead_id: str | None = None,
    slot_title: str | None = None,
    specialist: str | None = None,
):
    """
    Public GET endpoint — called when the Calendly booking link contains a
    redirect_uri pointing back here. Also useful for manual QA / testing.

    Usage (embedded in SMS link):
      https://calendly.com/nanditkalaria27
        ?lead_id=lead_b435b37821
        &booking_ref=cal_bk_51f1a50f89
        &redirect_uri=https://your-api.com/api/v1/calendly/confirm
    """
    from app.store import get_by_id as _gbi
    wid = "workspace_001"  # public endpoint — use default workspace
    if booking_ref:
        bk = _gbi("calendly_bookings", booking_ref)
        if bk:
            wid = bk.get("workspace_id") or wid
            lead_id = lead_id or bk.get("lead_id")
    from app.calendly_service import complete_calendly_booking
    result = complete_calendly_booking(
        workspace_id=wid,
        booking_id=booking_ref,
        lead_id=lead_id,
        slot_title=slot_title or "Northwind Digital Consultation",
        specialist=specialist or "Sarah Jenkins",
        notes="Booking confirmed via redirect link (post-Calendly scheduling).",
    )
    # Return a friendly HTML confirmation instead of JSON
    from fastapi.responses import HTMLResponse
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Booking Confirmed – Northwind Digital</title>
      <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               background: #f0f4ff; display: flex; align-items: center;
               justify-content: center; min-height: 100vh; margin: 0; }
        .card { background: white; border-radius: 16px; padding: 40px 36px;
                max-width: 440px; text-align: center; box-shadow: 0 8px 32px rgba(80,80,180,.10); }
        .icon { font-size: 48px; margin-bottom: 16px; }
        h1 { color: #1e293b; font-size: 22px; margin: 0 0 8px; }
        p  { color: #64748b; font-size: 15px; line-height: 1.6; margin: 0 0 24px; }
        .badge { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0;
                 border-radius: 99px; display: inline-block; padding: 6px 16px;
                 font-size: 13px; font-weight: 600; }
      </style>
    </head>
    <body>
      <div class="card">
        <div class="icon">🎉</div>
        <h1>You're all set!</h1>
        <p>Your consultation with the <strong>Northwind Digital</strong> team has been confirmed.
           You'll receive a calendar invite shortly with the call details.</p>
        <div class="badge">✓ Booking Confirmed</div>
      </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)


# ──────────────────────────────────────────────────────────────────────────────
# Calendly OAuth 2.0 — needed to get scheduled_events:read scope
# (Standard PATs from the Calendly UI only grant webhooks:read + webhooks:write)
#
# Setup: Create an OAuth app at https://developer.calendly.com
#   Redirect URI: http://localhost:8000/api/v1/calendly/oauth/callback
#   Set CALENDLY_CLIENT_ID + CALENDLY_CLIENT_SECRET in .env
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/v1/calendly/oauth/start")
def calendly_oauth_start():
    """
    Redirect the browser here to begin Calendly OAuth.
    Returns a redirect URL to send the user to Calendly for authorization.
    """
    from fastapi.responses import RedirectResponse
    client_id = os.getenv("CALENDLY_CLIENT_ID", "")
    if not client_id:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            "<h2>CALENDLY_CLIENT_ID not set in .env</h2>"
            "<p>Create an OAuth app at <a href='https://developer.calendly.com'>developer.calendly.com</a> "
            "then set CALENDLY_CLIENT_ID and CALENDLY_CLIENT_SECRET in .env</p>",
            status_code=400,
        )
    redirect_uri = os.getenv("API_BASE_URL", "http://localhost:8000") + "/api/v1/calendly/oauth/callback"
    auth_url = (
        f"https://auth.calendly.com/oauth/authorize"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
    )
    return RedirectResponse(url=auth_url)


@app.get("/api/v1/calendly/oauth/callback")
async def calendly_oauth_callback(code: str | None = None, error: str | None = None):
    """
    Calendly redirects here after the user authorizes the app.
    Exchanges the code for an access token, then auto-registers the webhook.
    """
    import httpx
    from fastapi.responses import HTMLResponse

    if error or not code:
        return HTMLResponse(f"<h2>OAuth Error: {error or 'No code returned'}</h2>", status_code=400)

    client_id     = os.getenv("CALENDLY_CLIENT_ID", "")
    client_secret = os.getenv("CALENDLY_CLIENT_SECRET", "")
    redirect_uri  = os.getenv("API_BASE_URL", "http://localhost:8000") + "/api/v1/calendly/oauth/callback"

    # Exchange code for access token
    async with httpx.AsyncClient(timeout=10.0) as client:
        token_resp = await client.post(
            "https://auth.calendly.com/oauth/token",
            data={
                "grant_type":    "authorization_code",
                "code":          code,
                "redirect_uri":  redirect_uri,
                "client_id":     client_id,
                "client_secret": client_secret,
            },
        )

    if token_resp.status_code != 200:
        return HTMLResponse(f"<h2>Token exchange failed: {token_resp.text}</h2>", status_code=400)

    token_data   = token_resp.json()
    access_token = token_data.get("access_token", "")
    org_uri      = token_data.get("organization", "")
    owner_uri    = token_data.get("owner", "")

    # Persist token to .env
    env_path = Path(__file__).parent.parent.parent / ".env"
    try:
        import re as _re
        txt = env_path.read_text()
        for key, val in [("CALENDLY_ACCESS_TOKEN", access_token)]:
            if f"{key}=" in txt:
                txt = _re.sub(rf"{key}=.*", f"{key}={val}", txt)
            else:
                txt += f"\n{key}={val}\n"
        env_path.write_text(txt)
        os.environ["CALENDLY_ACCESS_TOKEN"] = access_token
    except Exception:
        pass

    # Auto-register the webhook with the full-scope token
    api_host    = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
    webhook_url = f"{api_host}/api/v1/calendly/webhook"
    headers     = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    wh_result = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        wh_resp = await client.post(
            "https://api.calendly.com/webhook_subscriptions",
            headers=headers,
            json={
                "url":          webhook_url,
                "events":       ["invitee.created", "invitee.canceled"],
                "organization": org_uri or owner_uri,
                "user":         owner_uri,
                "scope":        "user",
            },
        )
        if wh_resp.status_code in (200, 201):
            wh_result = wh_resp.json().get("resource", {})
            signing_key = wh_result.get("signing_key", "")
            if signing_key:
                try:
                    import re as _re2
                    txt2 = env_path.read_text()
                    if "CALENDLY_WEBHOOK_SECRET=" in txt2:
                        txt2 = _re2.sub(r"CALENDLY_WEBHOOK_SECRET=.*", f"CALENDLY_WEBHOOK_SECRET={signing_key}", txt2)
                    else:
                        txt2 += f"\nCALENDLY_WEBHOOK_SECRET={signing_key}\n"
                    env_path.write_text(txt2)
                    os.environ["CALENDLY_WEBHOOK_SECRET"] = signing_key
                except Exception:
                    pass
        wh_status  = wh_resp.status_code
        wh_body    = wh_resp.text

    success = wh_status in (200, 201)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Calendly Connected – Northwind Digital</title>
  <style>
    body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
         background:#f0f4ff;display:flex;align-items:center;justify-content:center;
         min-height:100vh;margin:0;}}
    .card{{background:white;border-radius:16px;padding:40px 36px;max-width:480px;
           text-align:center;box-shadow:0 8px 32px rgba(80,80,180,.10);}}
    .icon{{font-size:48px;margin-bottom:16px;}}
    h1{{color:#1e293b;font-size:22px;margin:0 0 8px;}}
    p{{color:#64748b;font-size:14px;line-height:1.6;margin:0 0 20px;}}
    .badge{{background:#f0fdf4;color:#16a34a;border:1px solid #bbf7d0;
            border-radius:99px;display:inline-block;padding:6px 16px;
            font-size:13px;font-weight:600;margin-bottom:16px;}}
    .err{{background:#fef2f2;color:#dc2626;border:1px solid #fecaca;
          border-radius:8px;padding:12px;font-size:13px;margin-top:12px;text-align:left;}}
    .meta{{background:#f8fafc;border-radius:8px;padding:12px;font-size:12px;
           color:#64748b;text-align:left;margin-top:12px;}}
    .btn{{display:inline-block;margin-top:16px;padding:10px 24px;
          background:#6d28d9;color:white;border-radius:8px;text-decoration:none;
          font-size:14px;font-weight:600;}}
  </style>
</head>
<body><div class="card">
  <div class="icon">{'🎉' if success else '⚠️'}</div>
  <h1>{'Calendly Connected!' if success else 'OAuth Authorized – Webhook Issue'}</h1>
  {'<div class="badge">✓ Access Token Saved</div>' if access_token else ''}
  {'<div class="badge" style="background:#eff6ff;color:#1d4ed8;border-color:#bfdbfe">✓ Webhook Registered</div>' if success else ''}
  <p>
    {'Your Calendly account is fully connected. The AI will now auto-confirm bookings when leads schedule via the texted link.' if success else
     'Access token was saved. Webhook registration encountered an issue — check the error below.'}
  </p>
  {'<div class="err"><b>Webhook error:</b> ' + wh_body[:300] + '</div>' if not success else ''}
  <div class="meta">
    <b>Webhook URL:</b> {webhook_url}<br>
    <b>Events:</b> invitee.created, invitee.canceled<br>
    {'<b>Signing key:</b> saved to .env ✓' if success and wh_result.get('signing_key') else ''}
  </div>
  <a href="http://localhost:5173/app/calendly" class="btn">Back to Calendly Tracker →</a>
</div></body></html>"""

    return HTMLResponse(content=html, status_code=200)


class CalendlyRegisterWebhookIn(BaseModel):
    pat: str | None = None
    webhook_url: str | None = None
    user_uuid: str | None = None
    org_uuid: str | None = None


@app.post("/api/v1/calendly/register-webhook")
async def register_calendly_webhook(body: CalendlyRegisterWebhookIn, wid: str = Depends(workspace_id)):
    """
    Auto-registers the Calendly webhook subscription using a PAT.
    Required PAT scopes: webhooks:read, webhooks:write, scheduled_events:read
    """
    import httpx, base64

    pat = body.pat or os.getenv("CALENDLY_PAT", "")
    if not pat:
        raise HTTPException(400, "No Calendly PAT provided.")

    headers = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}

    # Decode user_uuid + scopes from JWT payload (no network call)
    try:
        parts = pat.split(".")
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        jwt_payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        user_uuid = body.user_uuid or jwt_payload.get("user_uuid")
        current_scopes = jwt_payload.get("scope", "")
    except Exception:
        raise HTTPException(400, "Could not decode PAT JWT.")

    # Check required scopes before making any API calls
    needed = ["webhooks:read", "webhooks:write", "scheduled_events:read"]
    missing = [s for s in needed if s not in current_scopes]
    if missing:
        return {
            "ok": False,
            "error": "insufficient_scopes",
            "current_scopes": current_scopes,
            "missing_scopes": missing,
            "action_required": (
                "Generate a new PAT at https://calendly.com/integrations/api_webhooks "
                f"and include these scopes: {', '.join(missing)}"
            ),
        }

    user_uri = f"https://api.calendly.com/users/{user_uuid}"
    org_uuid = body.org_uuid

    # Get organization URI from /users/me
    if not org_uuid:
        async with httpx.AsyncClient(timeout=8.0) as client:
            me = await client.get("https://api.calendly.com/users/me", headers=headers)
            if me.status_code == 200:
                org_uri_full = me.json().get("resource", {}).get("current_organization", "")
                org_uuid = org_uri_full.split("/")[-1] if org_uri_full else user_uuid
            else:
                org_uuid = user_uuid  # fallback: single-user org

    org_uri = f"https://api.calendly.com/organizations/{org_uuid}"
    api_host = (body.webhook_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    webhook_url = f"{api_host}/api/v1/calendly/webhook"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://api.calendly.com/webhook_subscriptions",
            headers=headers,
            json={
                "url": webhook_url,
                "events": ["invitee.created", "invitee.canceled"],
                "organization": org_uri,
                "user": user_uri,
                "scope": "user",
            },
        )

    if resp.status_code not in (200, 201):
        err = resp.json() if "application/json" in resp.headers.get("content-type", "") else {"raw": resp.text}
        details = [d.get("message", "") for d in (err.get("details") or [])]
        if any("missing required scope" in d for d in details):
            return {
                "ok": False,
                "error": "insufficient_scopes",
                "missing_scopes": details,
                "action_required": (
                    "Generate a new PAT at https://calendly.com/integrations/api_webhooks "
                    "with scopes: webhooks:read + webhooks:write + scheduled_events:read"
                ),
            }
        raise HTTPException(resp.status_code, str(err))

    wh = resp.json().get("resource", {})
    signing_key = wh.get("signing_key", "")

    # Persist signing key to .env
    env_path = Path(__file__).parent.parent.parent / ".env"
    env_updated = False
    try:
        if env_path.exists() and signing_key:
            import re as _re
            txt = env_path.read_text()
            if "CALENDLY_WEBHOOK_SECRET=" in txt:
                txt = _re.sub(r"CALENDLY_WEBHOOK_SECRET=.*", f"CALENDLY_WEBHOOK_SECRET={signing_key}", txt)
            else:
                txt += f"\nCALENDLY_WEBHOOK_SECRET={signing_key}\n"
            env_path.write_text(txt)
            os.environ["CALENDLY_WEBHOOK_SECRET"] = signing_key
            env_updated = True
    except Exception:
        pass

    return {
        "ok": True,
        "webhook_uri": wh.get("uri"),
        "webhook_url": webhook_url,
        "events": wh.get("events"),
        "signing_key": signing_key,
        "signing_key_saved_to_env": env_updated,
        "message": (
            f"Webhook registered! Calendly will POST to {webhook_url} on invitee events. "
            + ("Signing key saved to .env." if env_updated else "Copy signing_key to .env as CALENDLY_WEBHOOK_SECRET.")
        ),
    }


@app.post("/api/v1/calendly/track-and-recall")
def api_track_and_recall(body: CalendlyRecallIn | None = None, wid: str = Depends(workspace_id), user=Depends(current_user)):
    from app.calendly_service import check_unbooked_and_recall
    cid = body.campaign_id if body else None
    lid = body.lead_id if body else None
    force = body.force_immediate if body else True
    recalls = check_unbooked_and_recall(wid, campaign_id=cid, lead_id=lid, force_immediate=force, user=user)
    return {"ok": True, "recalls_executed": len(recalls), "recalls": recalls}


@app.post("/api/v1/calendly/schedule-callback")
def api_schedule_callback(body: CalendlyScheduleCallbackIn, wid: str = Depends(workspace_id)):
    """
    Manually schedule a callback for a lead at a user-entered time.
    Uses schedule_callback(), which fires Calendly's built-in confirmation
    email when CALENDLY_ACCESS_TOKEN + lead.email are available.
    Falls back to Twilio SMS otherwise.
    """
    from app.voice import parse_callback_request
    from app.calendly_service import schedule_callback
    parsed = parse_callback_request(body.time_text)
    if not parsed:
        raise HTTPException(400, f"Could not parse a time from: {body.time_text!r}")
    lead = get_by_id("leads", body.lead_id)
    if not lead or lead.get("workspace_id") != wid:
        raise HTTPException(404, "Lead not found")
    res = schedule_callback(
        workspace_id=wid,
        lead_id=body.lead_id,
        parsed=parsed,
        call_id=body.call_id,
        campaign_id=body.campaign_id,
        specialist=body.specialist,
        raw_user_text=body.time_text,
    )
    return {
        "ok": True,
        "delivery_channel": res.get("delivery_channel"),
        "calendly_event_uri": res.get("calendly_event_uri"),
        "calendly_link": res.get("calendly_link"),
        "email": res.get("email"),
        "phone": res.get("phone"),
        "booking_id": res["booking"]["id"],
        "parsed": parsed,
        "booking": res["booking"],
        "sms": res.get("sms"),
    }


@app.get("/api/v1/sms-logs")
def list_sms_logs(wid: str = Depends(workspace_id)):
    return by_workspace("sms_logs", wid)


@app.get("/api/v1/tasks")
def list_tasks(wid: str = Depends(workspace_id)):
    return by_workspace("tasks", wid)


@app.post("/api/v1/tasks")
def create_task(payload: dict, wid: str = Depends(workspace_id)):
    return create_record(
        "tasks",
        {
            **client_patch(payload),
            "id": new_id("task"),
            "workspace_id": wid,
            "created_at": utcnow(),
            "status": payload.get("status") or "open",
        },
    )


@app.patch("/api/v1/tasks/{tid}")
def patch_task(tid: str, body: TaskPatch, wid: str = Depends(workspace_id)):
    t = get_by_id("tasks", tid)
    if not t or t.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    return update_record("tasks", tid, {k: v for k, v in body.model_dump().items() if v is not None})


@app.post("/api/v1/copilot/ask")
def copilot(body: CopilotIn, wid: str = Depends(workspace_id)):
    return get_ai().copilot(body.question, wid)


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
        insights.append("Launch a qualification campaign on Nexus Cloud Systems to generate live insights.")
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
    return create_record(
        "saved_searches",
        {**body.model_dump(), "id": new_id("search"), "workspace_id": wid, "last_run_at": None, "created_at": utcnow()},
    )


@app.patch("/api/v1/saved-searches/{sid}")
def patch_search(sid: str, payload: dict, wid: str = Depends(workspace_id)):
    s = get_by_id("saved_searches", sid)
    if not s or s.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    return update_record("saved_searches", sid, client_patch(payload))


@app.post("/api/v1/saved-searches/{sid}/run")
def run_search(sid: str, wid: str = Depends(workspace_id), user=Depends(current_user)):
    s = get_by_id("saved_searches", sid)
    if not s or s.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    criteria = get_ai().plan_search(s.get("query") or "")
    matches = []
    for adapter in ADAPTERS:
        try:
            matches.extend(adapter.search(wid, criteria))
        except Exception:
            continue
    seen = set()
    unique = []
    for m in matches:
        key = m.get("id") or m.get("title")
        if key in seen:
            continue
        seen.add(key)
        unique.append(m)
    previous = set(s.get("match_ids") or [])
    new_ids = [m.get("id") for m in unique if m.get("id") and m.get("id") not in previous]
    ntf = None
    for m in unique:
        if m.get("id") and m.get("id") in new_ids:
            ntf = notifications_repo.create(
                {
                    "id": new_id("ntf"),
                    "workspace_id": wid,
                    "type": "radar",
                    "title": "New opportunity matched your saved search",
                    "body": f"{m.get('title') or m.get('requirement')} matched “{s.get('name')}”. Source: {m.get('source') or m.get('adapter')}. Detected {utcnow()[:10]}.",
                    "opportunity_id": m.get("id") if str(m.get("id", "")).startswith("opp_") else None,
                    "why_matched": f"Query “{s.get('query')}” matched title/requirement text.",
                    "source": m.get("source") or m.get("adapter"),
                    "detected_at": utcnow(),
                    "saved_search_id": sid,
                    "read": False,
                    "is_demo": True,
                    "created_at": utcnow(),
                }
            )
            break
    update_record(
        "saved_searches",
        sid,
        {
            "last_run_at": utcnow(),
            "match_ids": list({*(s.get("match_ids") or []), *[m.get("id") for m in unique if m.get("id")]}),
            "new_matches": len(new_ids),
        },
    )
    audit(wid, user["id"], "run_saved_search", "saved_search", sid)
    return {"matches": unique, "new_matches": len(new_ids), "notification": ntf, "label": "DEMO DATA"}


@app.get("/api/v1/notifications")
def list_ntf(wid: str = Depends(workspace_id)):
    return sorted(by_workspace("notifications", wid), key=lambda n: n.get("created_at") or "", reverse=True)


@app.post("/api/v1/notifications/{nid}/read")
def read_ntf(nid: str, wid: str = Depends(workspace_id)):
    n = get_by_id("notifications", nid)
    if not n or n.get("workspace_id") != wid:
        raise HTTPException(404, "Not found")
    return update_record("notifications", nid, {"read": True})


@app.post("/api/v1/notifications/read-all")
def read_all_ntf(wid: str = Depends(workspace_id)):
    out = []
    for n in by_workspace("notifications", wid):
        if not n.get("read"):
            out.append(update_record("notifications", n["id"], {"read": True}))
    return out


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


@app.post("/api/v1/admin/users/{uid}/status")
def admin_user_status(uid: str, status: str, admin=Depends(require_admin)):
    if status not in ("active", "suspended"):
        raise HTTPException(400, "status must be active or suspended")
    user = get_by_id("users", uid)
    if not user:
        raise HTTPException(404, "User not found")
    rec = update_record("users", uid, {"status": status})
    audit(None, admin["id"], "admin_user_status", "user", uid, {"status": status})
    return strip_user(rec or user)


@app.post("/api/v1/admin/campaigns/{cid}/pause")
def admin_pause(cid: str, admin=Depends(require_admin)):
    c = get_by_id("campaigns", cid)
    if not c:
        raise HTTPException(404, "Not found")
    rec = update_record("campaigns", cid, {"status": "paused"})
    audit(c.get("workspace_id"), admin["id"], "admin_pause_campaign", "campaign", cid)
    return rec


@app.post("/api/v1/admin/campaigns/{cid}/resume")
def admin_resume(cid: str, admin=Depends(require_admin)):
    c = get_by_id("campaigns", cid)
    if not c:
        raise HTTPException(404, "Not found")
    rec = update_record("campaigns", cid, {"status": "running"})
    audit(c.get("workspace_id"), admin["id"], "admin_resume_campaign", "campaign", cid)
    return rec


@app.get("/api/v1/opt-outs")
def list_opt(wid: str = Depends(workspace_id)):
    return by_workspace("opt_outs", wid)
