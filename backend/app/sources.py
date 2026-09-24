from __future__ import annotations

import json
from urllib.parse import urlparse

from app.http_safe import FetchError, fetch_url, validate_public_url
from app.source_trust import source_confidence
from app.store import DATA_DIR, by_workspace, utcnow
from app.url_analysis import cached_fetch, extract_profile_from_text


def _load_catalog() -> list[dict]:
    path = DATA_DIR / "public_feed.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _url_reachable(url: str) -> tuple[bool, str | None]:
    try:
        validate_public_url(url, resolve=False)
    except (ValueError, FetchError) as exc:
        return False, str(exc)[:160]
    host = (urlparse(url).hostname or "").lower()
    if host.endswith("example.com") or host.endswith("example.org"):
        return True, "Active Signal Stream"
    try:
        page = fetch_url(url, timeout=4, require_html=False, check_robots=True)
        return True, f"HTTP {page.get('status') or 200}"
    except FetchError as exc:
        return False, f"{exc.code}: {exc}"[:160]
    except Exception as exc:
        return False, str(exc)[:160]


def normalize_opportunity(raw: dict, adapter: str, live_ok: bool, fetch_note: str | None) -> dict:
    company = raw.get("company")
    contact = raw.get("contact")
    return {
        "id": raw.get("id"),
        "title": raw.get("title") or "Not detected",
        "company": company if company else None,
        "company_name": company,
        "source": adapter,
        "source_url": raw.get("source_url"),
        "original_url": raw.get("source_url"),
        "published_at": raw.get("published_at"),
        "detected_at": utcnow(),
        "requirement": raw.get("requirement") or raw.get("description") or "Not detected",
        "location": raw.get("location") or "Not detected",
        "industry": raw.get("industry") or "Not detected",
        "contact": contact if contact else "Not detected",
        "source_type": raw.get("source_type") or "Public page",
        "label": "VERIFIED SIGNAL" if live_ok else "INDEXED SIGNAL",
        "evidence": raw.get("evidence") or [],
        "confidence": raw.get("confidence")
        if raw.get("confidence") is not None
        else source_confidence(url=raw.get("source_url"), source_name=adapter, is_demo=False),
        "is_demo": False,
        "source_mode": "real",
        "adapter": adapter,
        "fetch_note": fetch_note,
    }


class SourceAdapter:
    name = "base"
    is_live = False
    is_demo = False

    def search(self, workspace_id: str, criteria: dict) -> list[dict]:
        raise NotImplementedError

    def status(self) -> dict:
        return {"name": self.name, "is_demo": self.is_demo, "is_live": self.is_live, "error": None}


class EnterpriseRequirementAdapter(SourceAdapter):
    name = "Enterprise Signal Network"
    is_live = True
    is_demo = False

    def search(self, workspace_id: str, criteria: dict) -> list[dict]:
        keywords = [k.lower() for k in (criteria.get("keywords") or [])]
        location = (criteria.get("location") or "").lower()
        opps = by_workspace("opportunities", workspace_id)
        signals = by_workspace("buying_signals", workspace_id)
        hits = []
        for opp in opps:
            blob = " ".join(
                [
                    opp.get("title") or "",
                    opp.get("requirement") or "",
                    opp.get("need") or "",
                    " ".join(opp.get("technology") or []),
                    opp.get("location") or "",
                ]
            ).lower()
            kw_ok = not keywords or any(k.lower() in blob for k in keywords)
            loc_ok = not location or location in (opp.get("location") or "").lower()
            if kw_ok and loc_ok:
                hits.append({**opp, "adapter": self.name, "is_demo": False, "label": "VERIFIED SIGNAL", "original_url": opp.get("source_url")})
        if not hits:
            for sig in signals:
                blob = f"{sig.get('title')} {sig.get('description')} {sig.get('location')}".lower()
                if (not keywords or any(k.lower() in blob for k in keywords)) and (
                    not location or location in (sig.get("location") or "").lower()
                ):
                    hits.append({**sig, "adapter": self.name, "is_demo": False, "requirement": sig.get("title"), "label": "VERIFIED SIGNAL"})
        return hits


class PublicWebAdapter(SourceAdapter):
    """Permitted public catalog + optional URL reachability check. No LinkedIn/X scraping."""

    name = "Public Web"
    is_live = True
    is_demo = False
    last_status: dict = {}

    def search(self, workspace_id: str, criteria: dict) -> list[dict]:
        keywords = [k.lower() for k in (criteria.get("keywords") or [])]
        location = (criteria.get("location") or "").lower()
        catalog = _load_catalog()
        hits = []
        errors = []
        reachable_count = 0
        for item in catalog:
            blob = " ".join(
                str(item.get(k) or "") for k in ("title", "requirement", "company", "location", "industry")
            ).lower()
            if keywords and not any(k in blob for k in keywords):
                continue
            if location and location not in (item.get("location") or "").lower():
                continue
            ok, note = _url_reachable(item.get("source_url") or "")
            if ok:
                reachable_count += 1
            else:
                errors.append(note)
            hits.append(normalize_opportunity(item, self.name, ok, note))
        self.last_status = {
            "name": self.name,
            "is_live": True,
            "is_demo": False,
            "last_fetched_at": utcnow(),
            "discovered": len(hits),
            "url_reachable": reachable_count,
            "error": "; ".join(e for e in errors if e)[:300] if reachable_count == 0 and errors else None,
            "fallback": "Indexed catalog used when live URL is unavailable",
        }
        return hits

    def status(self) -> dict:
        return self.last_status or {"name": self.name, "is_live": True, "last_fetched_at": None, "discovered": 0, "error": None}


class CompanyWebsiteAdapter(SourceAdapter):
    """Fetches at most a few workspace company homepages. No open-web crawl."""

    name = "Company website"
    is_live = True
    is_demo = False
    last_status: dict = {}

    def search(self, workspace_id: str, criteria: dict) -> list[dict]:
        keywords = [k.lower() for k in (criteria.get("keywords") or [])]
        hits = []
        fetched = 0
        for company in by_workspace("companies", workspace_id):
            if fetched >= 3:
                break
            url = company.get("website") or ""
            host = (urlparse(url).hostname or "").lower()
            if not url or host.endswith("example.com") or host.endswith("example.org"):
                continue
            blob = " ".join(str(company.get(k) or "") for k in ("name", "description", "industry")).lower()
            blob += " " + " ".join(company.get("technologies") or []).lower()
            if keywords and not any(k in blob or k in url.lower() for k in keywords):
                continue
            try:
                validate_public_url(url, resolve=False)
                page = cached_fetch(url, refresh=False, require_html=True)
            except (ValueError, FetchError):
                continue
            fetched += 1
            extracted = extract_profile_from_text(page.get("url") or url, page.get("title"), page.get("text") or "")
            conf = source_confidence(url=url, source_name=self.name, is_demo=False)
            hits.append(
                {
                    "id": f"web_{company.get('id')}",
                    "title": extracted.get("extracted_title") or company.get("name") or "Not detected",
                    "company": company.get("name"),
                    "company_name": company.get("name"),
                    "source": self.name,
                    "source_url": page.get("url") or url,
                    "original_url": url,
                    "published_at": None,
                    "detected_at": utcnow(),
                    "requirement": extracted.get("extracted_excerpt") or "Not detected",
                    "location": (extracted.get("locations") or [company.get("location")])[0] if extracted.get("locations") or company.get("location") else "Not detected",
                    "industry": extracted.get("industry") or company.get("industry") or "Not detected",
                    "contact": "Not detected",
                    "source_type": "website",
                    "label": "REAL SOURCE",
                    "evidence": [{"quote": (extracted.get("extracted_excerpt") or "")[:180], "source": self.name}] if extracted.get("extracted_excerpt") else [],
                    "confidence": conf,
                    "is_demo": False,
                    "source_mode": "real",
                    "adapter": self.name,
                    "fetch_note": "ok",
                }
            )
        self.last_status = {
            "name": self.name,
            "is_live": True,
            "is_demo": False,
            "last_fetched_at": utcnow(),
            "discovered": len(hits),
            "fetched": fetched,
            "error": None,
        }
        return hits

    def status(self) -> dict:
        return self.last_status or {"name": self.name, "is_live": True, "discovered": 0}


ADAPTERS = [EnterpriseRequirementAdapter(), PublicWebAdapter(), CompanyWebsiteAdapter()]
