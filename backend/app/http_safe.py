from __future__ import annotations

import ipaddress
import socket
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

USER_AGENT = "LuminaHackathonBot/0.1 (+https://localhost; public-source fetch)"
MAX_BYTES = 2_500_000
MAX_REDIRECTS = 3
TIMEOUT = 12
ALLOWED_SCHEMES = ("http", "https")
HTML_TYPES = ("text/html", "application/xhtml+xml")
BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "ip6-localhost",
    "metadata.google.internal",
}


class FetchError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class _LimitedRedirects(HTTPRedirectHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redirects = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.redirects += 1
        if self.redirects > MAX_REDIRECTS:
            raise FetchError("redirect_failure", "Too many redirects")
        validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _HrefExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        for k, v in attrs:
            if k == "href" and v:
                self.hrefs.append(v)


def _hostname_blocked(host: str) -> bool:
    h = (host or "").strip().lower().rstrip(".")
    if not h:
        return True
    if h in BLOCKED_HOSTS:
        return True
    if h.endswith(".localhost") or h.endswith(".local"):
        return True
    return False


NAT64_PREFIX = ipaddress.ip_network("64:ff9b::/96")
NAT64_LOCAL_PREFIX = ipaddress.ip_network("64:ff9b:1::/48")


def _ip_public(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
        return False
    if ip.version == 6 and (ip in NAT64_PREFIX or ip in NAT64_LOCAL_PREFIX):
        return True
    return bool(ip.is_global and not ip.is_reserved)


def validate_public_url(url: str, *, resolve: bool = True) -> str:
    raw = (url or "").strip()
    if not raw:
        raise ValueError("URL is required")
    parsed0 = urlparse(raw)
    scheme0 = (parsed0.scheme or "").lower()
    if scheme0 and scheme0 not in ALLOWED_SCHEMES:
        raise ValueError("Invalid URL")
    if scheme0 not in ALLOWED_SCHEMES:
        raw = "https://" + raw
        parsed0 = urlparse(raw)
        scheme0 = (parsed0.scheme or "").lower()
    if scheme0 not in ALLOWED_SCHEMES or not parsed0.netloc:
        raise ValueError("Invalid URL")
    host = parsed0.hostname
    if not host or _hostname_blocked(host):
        raise ValueError("localhost blocked")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and not _ip_public(ip):
        raise ValueError("private IP blocked")
    if resolve:
        try:
            infos = socket.getaddrinfo(host, parsed0.port or (443 if scheme0 == "https" else 80), type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise FetchError("dns_failure", str(exc)) from exc
        if not infos:
            raise FetchError("dns_failure", "Hostname did not resolve")
        for info in infos:
            addr = info[4][0]
            try:
                resolved = ipaddress.ip_address(addr)
            except ValueError:
                continue
            if not _ip_public(resolved):
                raise ValueError("private IP blocked")
    return raw


def robots_allows(url: str) -> bool:
    parsed = urlparse(url)
    robots = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        validate_public_url(robots, resolve=True)
        result = fetch_url(robots, accept="text/plain,*/*", check_robots=False, require_html=False)
        body = (result.get("text") or "").lower()
    except Exception:
        return True
    path = parsed.path or "/"
    ua_star = False
    disallows: list[str] = []
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("user-agent:"):
            ua_star = line.split(":", 1)[1].strip() == "*"
        elif ua_star and line.startswith("disallow:"):
            disallows.append(line.split(":", 1)[1].strip() or "/")
    for rule in disallows:
        if rule == "/" or (rule != "/" and path.startswith(rule)):
            return False
    return True


def fetch_url(
    url: str,
    *,
    timeout: float = TIMEOUT,
    max_bytes: int = MAX_BYTES,
    accept: str = "text/html,application/xhtml+xml",
    check_robots: bool = True,
    require_html: bool = False,
) -> dict:
    target = validate_public_url(url)
    if check_robots and not robots_allows(target):
        raise FetchError("robots", "Fetch blocked by robots.txt")
    opener = build_opener(_LimitedRedirects)
    req = Request(
        target,
        headers={"User-Agent": USER_AGENT, "Accept": accept},
    )
    try:
        with opener.open(req, timeout=timeout) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            clen = resp.headers.get("Content-Length")
            if clen:
                try:
                    if int(clen) > 15_000_000:
                        raise FetchError("oversized", "Response too large (>15MB)")
                except ValueError:
                    pass
            raw = resp.read(max_bytes)
            final_url = resp.geturl() or target
            status = getattr(resp, "status", 200)
    except FetchError:
        raise
    except HTTPError as exc:
        code = exc.code
        if code == 403:
            raise FetchError("http_403", "HTTP 403") from exc
        if code == 404:
            raise FetchError("http_404", "HTTP 404") from exc
        if code == 429:
            raise FetchError("http_429", "HTTP 429") from exc
        if code >= 500:
            raise FetchError("http_5xx", f"HTTP {code}") from exc
        raise FetchError("http_error", f"HTTP {code}") from exc
    except TimeoutError as exc:
        raise FetchError("timeout", "Request timed out") from exc
    except socket.timeout as exc:
        raise FetchError("timeout", "Request timed out") from exc
    except URLError as exc:
        reason = str(getattr(exc, "reason", exc)).lower()
        if "timed out" in reason:
            raise FetchError("timeout", "Request timed out") from exc
        raise FetchError("connection", str(getattr(exc, "reason", exc))[:200]) from exc
    except ValueError as exc:
        raise FetchError("invalid_url", str(exc)) from exc
    except OSError as exc:
        raise FetchError("connection", str(exc)[:200]) from exc

    raw = raw[:max_bytes]
    if require_html and not any(t in ctype for t in HTML_TYPES) and not raw.lstrip().startswith(b"<"):
        raise FetchError("content_type", "HTML only")
    text = raw.decode("utf-8", errors="ignore")
    return {
        "ok": True,
        "url": final_url,
        "status": status,
        "content_type": ctype,
        "text": text,
        "raw": raw,
    }


def same_host_links(base_url: str, html: str, keywords: tuple[str, ...]) -> list[str]:
    parser = _HrefExtractor()
    try:
        parser.feed(html)
    except Exception:
        return []
    base = urlparse(base_url)
    out: list[str] = []
    for href in parser.hrefs:
        abs_url = urljoin(base_url, href)
        parsed = urlparse(abs_url)
        if parsed.scheme not in ALLOWED_SCHEMES:
            continue
        if (parsed.hostname or "").lower() != (base.hostname or "").lower():
            continue
        blob = (parsed.path or "").lower() + " " + (parsed.query or "").lower()
        if any(k in blob for k in keywords):
            if abs_url not in out:
                out.append(abs_url)
    return out[:2]
