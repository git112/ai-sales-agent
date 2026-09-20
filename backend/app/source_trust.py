from __future__ import annotations

from urllib.parse import urlparse


def source_confidence(*, url: str | None = None, source_name: str | None = None, is_demo: bool = False) -> float:
    """Evidence-quality indicator, not a probability of truth."""
    if is_demo:
        return 0.55
    name = (source_name or "").lower()
    host = (urlparse(url or "").hostname or "").lower()
    if "demo" in name or host.endswith("example.com") or host.endswith("example.org"):
        return 0.55
    if host.startswith("www."):
        host = host[4:]
    path = (urlparse(url or "").path or "").lower()
    if any(k in path for k in ("/careers", "/jobs", "/news", "/press", "/about", "/blog")):
        return 0.84
    if "website" in name or "company" in name:
        return 0.88
    if host and "." in host:
        return 0.78
    return 0.4


def source_mode(*, is_demo: bool, fetch_ok: bool) -> str:
    if is_demo or not fetch_ok:
        return "demo"
    return "real"
