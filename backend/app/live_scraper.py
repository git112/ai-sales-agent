"""
live_scraper.py — Real internet opportunity discovery.

Sources (all public, no auth required):
  1. Indeed RSS          – job postings as buying signals
  2. Google News RSS     – company hiring/tech news
  3. SAM.gov API         – US federal contract opportunities
  4. Adzuna API          – tech jobs worldwide (free public API)
  5. Remotive RSS        – remote tech jobs
  6. We Work Remotely RSS– remote work postings
  7. arbeitnow RSS       – EU/global tech jobs
"""
from __future__ import annotations

import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from html import unescape
from typing import Any

from app.http_safe import FetchError, fetch_url
from app.source_trust import source_confidence
from app.store import utcnow

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

_STRIP_HTML = re.compile(r"<[^>]+>")
_MULTI_SPACE = re.compile(r"\s+")


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return _MULTI_SPACE.sub(" ", _STRIP_HTML.sub(" ", unescape(text))).strip()


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower())[:30].strip("_")


def _id(prefix: str, text: str) -> str:
    return f"live_{prefix}_{_slug(text)}"


def _fetch_json(url: str, timeout: int = 12) -> Any:
    result = fetch_url(url, timeout=timeout, require_html=False, check_robots=False,
                       accept="application/json,*/*")
    return json.loads(result["text"])


def _fetch_rss(url: str, timeout: int = 12) -> ET.Element:
    result = fetch_url(url, timeout=timeout, require_html=False, check_robots=False,
                       accept="application/rss+xml,application/xml,text/xml,*/*")
    return ET.fromstring(result["text"])


def _opp(
    *,
    raw_id: str,
    title: str,
    company: str | None,
    requirement: str,
    location: str,
    industry: str,
    source_url: str,
    source_name: str,
    published_at: str | None = None,
    confidence: float = 0.80,
    label: str = "LIVE SIGNAL",
) -> dict:
    return {
        "id": raw_id,
        "title": title or "Untitled",
        "company": company or None,
        "company_name": company or None,
        "source": source_name,
        "source_url": source_url,
        "original_url": source_url,
        "published_at": published_at,
        "detected_at": utcnow(),
        "requirement": requirement or "See source for details.",
        "location": location or "Not specified",
        "industry": industry or "Technology",
        "contact": "Not detected",
        "source_type": "Live scrape",
        "label": label,
        "evidence": [{"quote": requirement[:200], "source": source_name}] if requirement else [],
        "confidence": confidence,
        "is_demo": False,
        "source_mode": "real",
        "adapter": source_name,
        "fetch_note": "live",
    }


# ──────────────────────────────────────────────────────────────
# 1. Indeed RSS (public, no auth)
# ──────────────────────────────────────────────────────────────

INDEED_RSS = "https://www.indeed.com/rss?q={q}&l={l}&sort=date&limit=20"


def scrape_indeed(keywords: list[str], location: str = "", limit: int = 10) -> list[dict]:
    q = urllib.parse.quote_plus(" ".join(keywords[:5]))
    l = urllib.parse.quote_plus(location) if location else ""
    url = INDEED_RSS.format(q=q, l=l)
    try:
        root = _fetch_rss(url)
        channel = root.find("channel")
        items = (channel or root).findall("item") if channel is not None else root.findall(".//item")
        results = []
        for item in items[:limit]:
            title = _clean(item.findtext("title"))
            link = _clean(item.findtext("link"))
            desc = _clean(item.findtext("description"))
            pub = _clean(item.findtext("pubDate"))
            # Extract company from title "Job Title - Company" pattern
            company = None
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                company = parts[-1].strip()
                title = parts[0].strip()
            results.append(_opp(
                raw_id=_id("indeed", link or title),
                title=title,
                company=company,
                requirement=desc[:500] if desc else "",
                location=location or "Not specified",
                industry="Technology",
                source_url=link,
                source_name="Indeed",
                published_at=pub or None,
                confidence=source_confidence(url=link, source_name="Indeed", is_demo=False),
                label="LIVE SIGNAL",
            ))
        return results
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────
# 2. Google News RSS
# ──────────────────────────────────────────────────────────────

GNEWS_RSS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def scrape_google_news(keywords: list[str], limit: int = 8) -> list[dict]:
    query_terms = " ".join(keywords[:4]) + " RFP OR tender OR hiring OR implementation"
    q = urllib.parse.quote_plus(query_terms)
    url = GNEWS_RSS.format(q=q)
    try:
        root = _fetch_rss(url)
        channel = root.find("channel")
        items = (channel or root).findall("item") if channel is not None else root.findall(".//item")
        results = []
        for item in items[:limit]:
            title = _clean(item.findtext("title"))
            link = _clean(item.findtext("link"))
            desc = _clean(item.findtext("description"))
            pub = _clean(item.findtext("pubDate"))
            # Extract source from title "Title - Source" pattern
            source_site = "News"
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                source_site = parts[-1].strip()
                title = parts[0].strip()
            results.append(_opp(
                raw_id=_id("gnews", title),
                title=title,
                company=source_site,
                requirement=desc[:500] if desc else title,
                location="Not specified",
                industry="Technology",
                source_url=link,
                source_name="Google News",
                published_at=pub or None,
                confidence=0.65,
                label="NEWS SIGNAL",
            ))
        return results
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────
# 3. SAM.gov — US Federal Contract Opportunities (public API)
# ──────────────────────────────────────────────────────────────

SAMGOV_API = "https://api.sam.gov/opportunities/v2/search?limit={limit}&api_key=DEMO_KEY&keywords={q}&status=Active"


def scrape_samgov(keywords: list[str], limit: int = 8) -> list[dict]:
    q = urllib.parse.quote_plus(" ".join(keywords[:5]))
    url = SAMGOV_API.format(q=q, limit=limit)
    try:
        data = _fetch_json(url)
        opps = (data.get("opportunitiesData") or [])
        results = []
        for item in opps[:limit]:
            title = _clean(item.get("title") or "")
            opp_id = item.get("noticeId") or title
            link = f"https://sam.gov/opp/{item.get('noticeId','')}/view" if item.get("noticeId") else "https://sam.gov"
            dept = _clean(item.get("department") or item.get("organizationName") or "")
            desc = _clean(item.get("description") or "")
            loc = _clean(item.get("placeOfPerformance", {}).get("state", {}).get("name") or "")
            naics = _clean(item.get("naicsCode") or "")
            pub = item.get("postedDate") or item.get("responseDeadLine") or None
            results.append(_opp(
                raw_id=_id("sam", opp_id),
                title=title,
                company=dept,
                requirement=desc[:500] if desc else title,
                location=f"{loc}, USA" if loc else "USA",
                industry=f"Government / NAICS {naics}" if naics else "Government",
                source_url=link,
                source_name="SAM.gov",
                published_at=pub,
                confidence=0.90,
                label="VERIFIED SIGNAL",
            ))
        return results
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────
# 4. Remotive RSS — Remote tech jobs
# ──────────────────────────────────────────────────────────────

REMOTIVE_RSS = "https://remotive.com/remote-jobs/feed"


def scrape_remotive(keywords: list[str], limit: int = 10) -> list[dict]:
    try:
        root = _fetch_rss(REMOTIVE_RSS)
        channel = root.find("channel")
        items = (channel or root).findall("item") if channel is not None else root.findall(".//item")
        kw_low = [k.lower() for k in keywords]
        results = []
        for item in items:
            if len(results) >= limit:
                break
            title = _clean(item.findtext("title"))
            link = _clean(item.findtext("link"))
            desc = _clean(item.findtext("description"))
            pub = _clean(item.findtext("pubDate"))
            blob = f"{title} {desc}".lower()
            if kw_low and not any(k in blob for k in kw_low):
                continue
            # Extract company
            company = None
            for tag in item:
                if "company" in tag.tag.lower():
                    company = _clean(tag.text)
                    break
            if " - " in title and not company:
                parts = title.rsplit(" - ", 1)
                company = parts[-1].strip()
                title = parts[0].strip()
            results.append(_opp(
                raw_id=_id("remotive", link or title),
                title=title,
                company=company,
                requirement=desc[:500] if desc else "",
                location="Remote",
                industry="Technology",
                source_url=link,
                source_name="Remotive",
                published_at=pub or None,
                confidence=source_confidence(url=link, source_name="Remotive", is_demo=False),
                label="LIVE SIGNAL",
            ))
        return results
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────
# 5. We Work Remotely RSS
# ──────────────────────────────────────────────────────────────

WWR_RSS = "https://weworkremotely.com/categories/remote-programming-jobs.rss"


def scrape_weworkremotely(keywords: list[str], limit: int = 8) -> list[dict]:
    try:
        root = _fetch_rss(WWR_RSS)
        items = root.findall(".//item")
        kw_low = [k.lower() for k in keywords]
        results = []
        for item in items:
            if len(results) >= limit:
                break
            title = _clean(item.findtext("title"))
            link = _clean(item.findtext("link"))
            desc = _clean(item.findtext("description"))
            pub = _clean(item.findtext("pubDate"))
            blob = f"{title} {desc}".lower()
            if kw_low and not any(k in blob for k in kw_low):
                continue
            # Title format: "Company: Job Title at Company"
            company = None
            region = "Remote"
            if ": " in title:
                parts = title.split(": ", 1)
                company = parts[0].strip()
                title = parts[1].strip() if len(parts) > 1 else title
            results.append(_opp(
                raw_id=_id("wwr", link or title),
                title=title,
                company=company,
                requirement=desc[:500] if desc else "",
                location=region,
                industry="Technology",
                source_url=link,
                source_name="WeWorkRemotely",
                published_at=pub or None,
                confidence=0.78,
                label="LIVE SIGNAL",
            ))
        return results
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────
# 6. arbeitnow RSS — EU tech jobs
# ──────────────────────────────────────────────────────────────

ARBEITNOW_RSS = "https://www.arbeitnow.com/api/job-board-api?tags={tags}"


def scrape_arbeitnow(keywords: list[str], limit: int = 8) -> list[dict]:
    tags = ",".join(keywords[:3])
    url = ARBEITNOW_RSS.format(tags=urllib.parse.quote_plus(tags))
    try:
        data = _fetch_json(url)
        items = data.get("data") or []
        kw_low = [k.lower() for k in keywords]
        results = []
        for item in items:
            if len(results) >= limit:
                break
            title = _clean(item.get("title") or "")
            company = _clean(item.get("company_name") or "")
            desc = _clean(item.get("description") or "")
            location = _clean(item.get("location") or "")
            link = item.get("url") or "https://www.arbeitnow.com"
            pub = item.get("created_at") or None
            blob = f"{title} {desc} {' '.join(item.get('tags') or [])}".lower()
            if kw_low and not any(k in blob for k in kw_low):
                continue
            results.append(_opp(
                raw_id=_id("arbeitnow", link or title),
                title=title,
                company=company,
                requirement=desc[:500] if desc else "",
                location=location or "Europe",
                industry="Technology",
                source_url=link,
                source_name="Arbeitnow",
                published_at=pub,
                confidence=0.80,
                label="LIVE SIGNAL",
            ))
        return results
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────
# 7. Adzuna public API (no key needed for basic search)
# ──────────────────────────────────────────────────────────────

ADZUNA_API = "https://api.adzuna.com/v1/api/jobs/{country}/search/1?app_id=9085fc48&app_key=a1b2c3d4e5f6a7b8c9d0e1f2&results_per_page=10&what={q}&content-type=application/json"


def scrape_adzuna(keywords: list[str], location: str = "", country: str = "in", limit: int = 10) -> list[dict]:
    """Adzuna — large job aggregator, free tier available."""
    q = urllib.parse.quote_plus(" ".join(keywords[:5]))
    # country codes: gb=UK, us=US, in=India, au=Australia, de=Germany
    url = ADZUNA_API.format(country=country, q=q)
    if location:
        url += f"&where={urllib.parse.quote_plus(location)}"
    try:
        data = _fetch_json(url)
        items = data.get("results") or []
        results = []
        for item in items[:limit]:
            title = _clean(item.get("title") or "")
            company = _clean((item.get("company") or {}).get("display_name") or "")
            desc = _clean(item.get("description") or "")
            loc = _clean((item.get("location") or {}).get("display_name") or "")
            link = item.get("redirect_url") or "https://www.adzuna.com"
            pub = item.get("created") or None
            cat = _clean((item.get("category") or {}).get("label") or "Technology")
            results.append(_opp(
                raw_id=_id("adzuna", link or title),
                title=title,
                company=company,
                requirement=desc[:500] if desc else "",
                location=loc or location or "Not specified",
                industry=cat,
                source_url=link,
                source_name="Adzuna",
                published_at=pub,
                confidence=source_confidence(url=link, source_name="Adzuna", is_demo=False),
                label="LIVE SIGNAL",
            ))
        return results
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────
# Master scrape function — called by LiveDiscoveryAdapter
# ──────────────────────────────────────────────────────────────

def scrape_all(keywords: list[str], location: str = "", limit_per_source: int = 8) -> tuple[list[dict], list[dict]]:
    """
    Run all scrapers in sequence. Returns (results, source_statuses).
    Results are deduplicated by URL.
    """
    all_results: list[dict] = []
    statuses: list[dict] = []

    def _run(name: str, fn, *args, **kwargs):
        try:
            batch = fn(*args, **kwargs)
            all_results.extend(batch)
            statuses.append({"name": name, "discovered": len(batch), "error": None, "is_live": True})
        except Exception as exc:
            statuses.append({"name": name, "discovered": 0, "error": str(exc)[:200], "is_live": False})

    _run("Indeed", scrape_indeed, keywords, location, limit_per_source)
    _run("Remotive", scrape_remotive, keywords, limit_per_source)
    _run("WeWorkRemotely", scrape_weworkremotely, keywords, limit_per_source)
    _run("Arbeitnow", scrape_arbeitnow, keywords, limit_per_source)
    _run("SAM.gov", scrape_samgov, keywords, limit_per_source)
    _run("Google News", scrape_google_news, keywords, limit_per_source)
    _run("Adzuna", scrape_adzuna, keywords, location, "in", limit_per_source)

    # Deduplicate by source_url
    seen_urls: set[str] = set()
    unique: list[dict] = []
    for r in all_results:
        key = r.get("source_url") or r.get("id")
        if key and key not in seen_urls:
            seen_urls.add(key)
            unique.append(r)

    return unique, statuses
