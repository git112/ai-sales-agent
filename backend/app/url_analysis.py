from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlparse

from app.core.config import settings
from app.http_safe import FetchError, fetch_url, validate_public_url
from app.source_trust import source_confidence, source_mode
from app.store import utcnow

log = logging.getLogger("lumina.url_analysis")

MAX_BYTES = 80_000
TIMEOUT = 6
USER_AGENT = "LuminaHackathonBot/0.1 (+https://localhost; demo URL analysis)"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip = 0
        self.parts: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "nav", "footer", "header", "svg"):
            self._skip += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "nav", "footer", "header", "svg") and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        text = " ".join((data or "").split())
        if not text:
            return
        if self._in_title:
            self.title = text
        if self._skip == 0:
            self.parts.append(text)


def validate_url(url: str) -> str:
    """Public HTTP/HTTPS only. Rejects localhost, private IPs, and non-web schemes."""
    try:
        return validate_public_url(url, resolve=False)
    except FetchError as exc:
        raise ValueError(str(exc)) from exc


def _robots_allows(url: str) -> bool:
    from app.http_safe import robots_allows

    return robots_allows(url)


def fetch_visible_text(url: str) -> dict:
    try:
        page = fetch_url(url, timeout=TIMEOUT, max_bytes=MAX_BYTES, require_html=True, check_robots=True)
    except FetchError as exc:
        return {"ok": False, "error": str(exc), "error_code": exc.code, "title": None, "text": ""}
    except ValueError as exc:
        return {"ok": False, "error": str(exc), "error_code": "invalid_url", "title": None, "text": ""}
    raw = page.get("raw") or b""
    parser = _TextExtractor()
    try:
        parser.feed((page.get("text") or raw.decode("utf-8", errors="ignore")))
    except Exception:
        return {"ok": False, "error": "Could not parse HTML", "error_code": "invalid_html", "title": None, "text": ""}
    text = " ".join(parser.parts)[:8000]
    if not text.strip():
        return {"ok": False, "error": "Empty HTML text", "error_code": "invalid_html", "title": parser.title or None, "text": ""}
    return {
        "ok": True,
        "error": None,
        "error_code": None,
        "title": parser.title or None,
        "text": text,
        "url": page.get("url") or url,
        "content_type": page.get("content_type"),
    }


def _cache_key(url: str) -> str:
    return "url_cache:" + hashlib.sha256(url.encode("utf-8")).hexdigest()


def cached_fetch(url: str, *, refresh: bool = False, require_html: bool = True) -> dict:
    from app.db import meta_get, meta_set, sqlite_active

    if not refresh and sqlite_active():
        raw = meta_get(_cache_key(url))
        if raw:
            try:
                payload = json.loads(raw)
                ts = datetime.fromisoformat((payload.get("fetched_at") or "").replace("Z", "+00:00"))
                ttl = float(getattr(settings, "url_cache_ttl_seconds", 21600) or 21600)
                if (datetime.now(timezone.utc) - ts).total_seconds() <= ttl:
                    payload["from_cache"] = True
                    return payload
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
    fetched = fetch_visible_text(url) if require_html else None
    if fetched is None:
        page = fetch_url(url, require_html=False, check_robots=True)
        fetched = {"ok": True, "text": page.get("text") or "", "title": None, "url": page.get("url") or url}
    if not fetched.get("ok"):
        raise FetchError(fetched.get("error_code") or "connection", fetched.get("error") or "Fetch failed")
    payload = {
        "ok": True,
        "url": fetched.get("url") or url,
        "title": fetched.get("title"),
        "text": (fetched.get("text") or "")[:8000],
        "fetched_at": utcnow(),
        "from_cache": False,
    }
    if sqlite_active():
        meta_set(_cache_key(url), json.dumps(payload, ensure_ascii=False))
    return payload


def extract_profile_from_text(url: str, title: str | None, text: str) -> dict:
    blob = f"{title or ''} {text}".lower()
    host = urlparse(url).hostname or ""
    name = (title or "").split("|")[0].split("–")[0].strip() or host.replace("www.", "")
    services, techs, keywords, pains, signals, roles = [], [], [], [], [], []
    mapping = [
        ("sharepoint", "SharePoint implementation", "SharePoint"),
        ("microsoft 365", "Microsoft 365 consulting", "Microsoft 365"),
        ("office 365", "Microsoft 365 consulting", "Microsoft 365"),
        ("migration", "SharePoint migration", "migration"),
        ("intranet", "Intranet / digital workplace", "intranet"),
        ("document", "Enterprise document management", "document management"),
    ]
    for term, service, kw in mapping:
        if term in blob:
            if service not in services:
                services.append(service)
            if kw not in techs and kw[0].isupper():
                techs.append(kw)
            if kw not in keywords:
                keywords.append(kw)
    locations = []
    for loc in ["india", "uae", "pune", "mumbai", "chennai", "ahmedabad", "united states"]:
        if loc in blob:
            locations.append(loc.title() if loc != "uae" else "UAE")
    if any(x in blob for x in ("we are hiring", "we're hiring", "join our team", "careers")):
        roles.append("Hiring mentioned on public website")
        signals.append("Public hiring language")
    if "sharepoint" in blob and any(x in blob for x in ("looking for", "challenge", "need help")):
        pains.append("Need for structured SharePoint implementation or migration")
    excerpt = (text[:400] if text else None)
    conf = source_confidence(url=url, source_name="website", is_demo=False)
    facts = []
    if name:
        facts.append(_fact("company_name", name, url, excerpt, conf))
    if services:
        facts.append(_fact("services", services, url, excerpt, conf))
    if techs:
        facts.append(_fact("technologies", techs, url, excerpt, conf))
    return {
        "company_name": name or None,
        "website": url,
        "industry": "IT consulting" if "consult" in blob or "sharepoint" in blob else None,
        "products_services": services or None,
        "target_customers": None,
        "technologies": techs or None,
        "locations": locations or None,
        "business_keywords": keywords or None,
        "likely_pain_points": pains or None,
        "likely_buying_signals": signals or None,
        "target_roles": roles or None,
        "extracted_title": title,
        "extracted_excerpt": excerpt,
        "facts": facts,
        "source_url": url,
        "source_type": "website",
        "retrieved_at": utcnow(),
        "confidence": conf,
    }


def _fact(field: str, value, url: str, excerpt: str | None, confidence: float) -> dict:
    return {
        "field": field,
        "value": value,
        "source_url": url,
        "source_type": "website",
        "evidence": excerpt,
        "confidence": confidence,
        "retrieved_at": utcnow(),
        "is_demo": False,
    }


def demo_fallback_northwind(url: str) -> dict:
    now = utcnow()
    return {
        "company_name": "Northwind Digital",
        "website": url,
        "industry": "IT consulting",
        "products_services": [
            "SharePoint implementation",
            "SharePoint migration",
            "Microsoft 365 consulting",
        ],
        "target_customers": ["CIO", "IT Director", "SharePoint Admin"],
        "technologies": ["SharePoint", "Microsoft 365"],
        "locations": ["Ahmedabad, India", "India", "UAE"],
        "business_keywords": ["SharePoint implementation", "migration"],
        "likely_pain_points": ["Intranet modernization", "Document management on Microsoft 365"],
        "likely_buying_signals": ["Posted SharePoint implementation or migration requirements"],
        "extracted_title": "Northwind Digital (demo catalog)",
        "extracted_excerpt": None,
        "label": "DEMO DATA",
        "source": "Demo catalog fallback",
        "source_type": "demo_catalog",
        "source_url": url,
        "source_mode": "demo",
        "confidence": 0.55,
        "fetch_status": "failed_fallback",
        "is_demo": True,
        "retrieved_at": now,
    }


def analyze_website(url: str, *, refresh: bool = False) -> dict:
    """Fetch → extract → metadata. Never sends the raw URL to an LLM."""
    try:
        safe = validate_url(url)
    except ValueError as exc:
        raise
    try:
        fetched = cached_fetch(safe, refresh=refresh, require_html=True)
    except FetchError as exc:
        host = (urlparse(safe).hostname or "").lower()
        if "northwind" in host or host.endswith("example.com") or host.endswith("example.org"):
            fb = demo_fallback_northwind(safe)
            fb["fetch_error"] = str(exc)
            fb["error_code"] = exc.code
            return fb
        return {
            "company_name": None,
            "website": safe,
            "industry": None,
            "products_services": None,
            "target_customers": None,
            "technologies": None,
            "locations": None,
            "business_keywords": None,
            "likely_pain_points": None,
            "likely_buying_signals": None,
            "company_summary": None,
            "label": "Not detected",
            "source": "Fetch failed — no invented data",
            "source_type": "website",
            "source_url": safe,
            "source_mode": "demo",
            "fetch_status": "failed",
            "is_demo": False,
            "confidence": 0,
            "fetch_error": str(exc),
            "error_code": exc.code,
            "retrieved_at": utcnow(),
        }
    extracted = extract_profile_from_text(fetched.get("url") or safe, fetched.get("title"), fetched.get("text") or "")
    extracted.update(
        {
            "label": "REAL SOURCE",
            "source": "Public website fetch",
            "source_mode": source_mode(is_demo=False, fetch_ok=True),
            "fetch_status": "ok",
            "is_demo": False,
            "from_cache": bool(fetched.get("from_cache")),
            "retrieved_at": fetched.get("fetched_at") or utcnow(),
        }
    )
    return extracted
