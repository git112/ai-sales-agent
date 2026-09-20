from __future__ import annotations

import logging

from app.http_safe import FetchError, validate_public_url
from app.source_trust import source_confidence
from app.store import by_workspace, create_record, get_by_id, new_id, utcnow
from app.url_analysis import cached_fetch

log = logging.getLogger("lumina.intel")

SIGNAL_PATTERNS = [
    (
        "hiring",
        "Hiring",
        ("we are hiring", "we're hiring", "join our team", "open roles", "job opening", "careers", "sharepoint administrator"),
        "Public hiring/careers language on the company site.",
    ),
    (
        "funding",
        "Funding",
        ("series a", "series b", "raised funding", "venture capital", "seed round"),
        "Public funding language on the company site.",
    ),
    (
        "technology_stack",
        "Technology signal",
        ("sharepoint", "microsoft 365", "office 365", "power platform", "azure"),
        "Public technology reference on the company site.",
    ),
    (
        "expansion",
        "Business announcement",
        ("expansion", "new office", "opening a delivery", "headcount growth"),
        "Public expansion/business announcement on the company site.",
    ),
    (
        "growth",
        "Business announcement",
        ("year-over-year growth", "record revenue", "growing our team"),
        "Public growth language on the company site.",
    ),
]


def _quote_around(blob: str, term: str, limit: int = 180) -> str | None:
    low = blob.lower()
    idx = low.find(term)
    if idx < 0:
        return None
    start = max(0, idx - 40)
    end = min(len(blob), idx + len(term) + 80)
    snippet = " ".join(blob[start:end].split())
    return snippet[:limit] or None


def extract_signals_from_text(
    *,
    url: str,
    text: str,
    title: str | None = None,
    company_id: str | None = None,
    opportunity_id: str | None = None,
    workspace_id: str | None = None,
    source_name: str = "Company website",
    is_demo: bool = False,
) -> list[dict]:
    from urllib.parse import urlparse

    blob = f"{title or ''} {text}"
    now = utcnow()
    host = urlparse(url).hostname or ""
    if host.endswith("example.com") or host.endswith("example.org"):
        is_demo = True
    conf = source_confidence(url=url, source_name=source_name, is_demo=is_demo)
    rows = []
    seen = set()
    for kind, signal_type, terms, summary in SIGNAL_PATTERNS:
        quote = None
        hit = None
        for term in terms:
            quote = _quote_around(blob, term)
            if quote:
                hit = term
                break
        if not quote:
            continue
        key = (kind, hit)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "id": new_id("ms"),
                "workspace_id": workspace_id,
                "company_id": company_id,
                "opportunity_id": opportunity_id,
                "kind": kind,
                "signal_type": signal_type,
                "title": f"{signal_type} evidence from {host or 'website'}",
                "summary": summary,
                "source": source_name,
                "source_name": source_name,
                "source_url": url,
                "source_type": "website",
                "evidence": quote,
                "confidence": conf,
                "detected": True,
                "observed_at": now,
                "retrieved_at": now,
                "last_updated": now,
                "is_demo": is_demo,
                "status": "observed",
                "label": "DEMO DATA" if is_demo else "REAL SOURCE",
            }
        )
    return rows


def persist_new_market_signals(existing: list[dict], fresh: list[dict]) -> list[dict]:
    known = {(m.get("source_url"), m.get("kind")) for m in existing}
    created = []
    for row in fresh:
        key = (row.get("source_url"), row.get("kind"))
        if key in known:
            continue
        if not row.get("evidence"):
            continue
        created.append(create_record("market_signals", row))
        known.add(key)
    return created


def refresh_opportunity_intel(opportunity: dict, *, refresh: bool = False) -> list[dict]:
    """Bounded company-website fetch. Skips demo/example hosts. Never crawls the open web."""
    from urllib.parse import urlparse

    from app.http_safe import same_host_links

    oid = opportunity.get("id")
    wid = opportunity.get("workspace_id")
    company = get_by_id("companies", opportunity.get("company_id") or "") or {}
    url = company.get("website") or opportunity.get("source_url")
    existing = [m for m in by_workspace("market_signals", wid or "") if m.get("opportunity_id") == oid]
    if not url:
        return existing
    try:
        validate_public_url(url, resolve=False)
    except (ValueError, FetchError):
        return existing
    host = (urlparse(url).hostname or "").lower()
    if host.endswith("example.com") or host.endswith("example.org"):
        return existing
    try:
        fetched = cached_fetch(url, refresh=refresh, require_html=True)
    except FetchError as exc:
        log.warning("market intel fetch skipped (%s)", exc.code)
        return existing
    text = fetched.get("text") or ""
    title = fetched.get("title")
    fresh = extract_signals_from_text(
        url=fetched.get("url") or url,
        text=text,
        title=title,
        company_id=company.get("id"),
        opportunity_id=oid,
        workspace_id=wid,
        is_demo=False,
    )
    for extra in same_host_links(fetched.get("url") or url, text, ("career", "job", "news", "press")):
        try:
            page = cached_fetch(extra, refresh=refresh, require_html=True)
        except FetchError:
            continue
        fresh.extend(
            extract_signals_from_text(
                url=page.get("url") or extra,
                text=page.get("text") or "",
                title=page.get("title"),
                company_id=company.get("id"),
                opportunity_id=oid,
                workspace_id=wid,
                source_name="Company public page",
                is_demo=False,
            )
        )
    persist_new_market_signals(existing, fresh)
    return [m for m in by_workspace("market_signals", wid or "") if m.get("opportunity_id") == oid]
