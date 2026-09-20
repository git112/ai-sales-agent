import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
checks = []


def req(method, path, data=None, token=None, extra=None):
    headers = {}
    body = None
    if token:
        headers["Authorization"] = "Bearer " + token
        headers["X-Workspace-Id"] = "workspace_001"
    if extra:
        headers.update(extra)
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    r = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            raw = resp.read()
            parsed = json.loads(raw) if raw else None
            return resp.status, parsed
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:240]


def mark(name, ok, status):
    checks.append((name, bool(ok), status))


s, health = req("GET", "/health")
mark("health", s == 200, s)

s, login = req("POST", "/api/v1/auth/login", {"email": "demo@example.com", "password": "Demo123!"})
mark("login user", s == 200 and login.get("user", {}).get("email") == "demo@example.com", s)
tok = login["token"] if s == 200 else None

s, admin = req("POST", "/api/v1/auth/login", {"email": "admin@example.com", "password": "Admin123!"})
mark("login admin", s == 200 and admin.get("user", {}).get("role") == "admin", s)
at = admin["token"] if s == 200 else None


def G(path):
    return req("GET", path, token=tok)


def P(path, body):
    return req("POST", path, body, token=tok)


for name, path in [
    ("me", "/api/v1/auth/me"),
    ("workspaces", "/api/v1/workspaces"),
    ("mode", "/api/v1/workspaces/workspace_001/mode"),
    ("profile", "/api/v1/business-profile"),
    ("knowledge", "/api/v1/knowledge"),
    ("opps", "/api/v1/opportunities"),
    ("opp abc", "/api/v1/opportunities/opp_abc"),
    ("evidence", "/api/v1/opportunities/opp_abc/evidence"),
    ("enrich", "/api/v1/opportunities/opp_abc/enrichment"),
    ("market", "/api/v1/opportunities/opp_abc/market-intelligence"),
    ("signals", "/api/v1/buying-signals"),
    ("leads", "/api/v1/leads"),
    ("pipeline", "/api/v1/leads/pipeline"),
    ("lead abc", "/api/v1/leads/lead_abc"),
    ("segments", "/api/v1/segments"),
    ("agents", "/api/v1/voice-agents"),
    ("agent", "/api/v1/voice-agents/agent_001"),
    ("campaigns", "/api/v1/campaigns"),
    ("calls", "/api/v1/calls"),
    ("tasks", "/api/v1/tasks"),
    ("dashboard", "/api/v1/dashboard"),
    ("analytics", "/api/v1/analytics/calls"),
    ("saved", "/api/v1/saved-searches"),
    ("ntf", "/api/v1/notifications"),
    ("optouts", "/api/v1/opt-outs"),
]:
    st, _ = G(path)
    mark(name, st == 200, st)

st, body = P("/api/v1/opportunities/search", {"query": "Find companies looking for SharePoint implementation"})
mark("search", st == 200 and "Demo Source" in str(body), st)
st, body = P("/api/v1/opportunities/opp_abc/analyze", {})
mark("analyze", st == 200 and (body or {}).get("analysis", {}).get("total"), st)
st, body = P("/api/v1/copilot/ask", {"question": "Show high-intent leads."})
mark("copilot", st == 200 and (body or {}).get("grounded") is True, st)
st, pg = P(
    "/api/v1/voice-agents/agent_001/playground",
    {
        "message": "We are looking for SharePoint migration support and want to start this month.",
        "history": [],
        "language": "en",
    },
)
mark("playground high intent", st == 200 and (pg or {}).get("qualification", {}).get("high_intent") is True, st)
st, camp = P(
    "/api/v1/campaigns",
    {
        "name": "Audit campaign",
        "campaign_type": "leads_plus_calling",
        "objective": "q",
        "agent_id": "agent_001",
        "lead_ids": ["lead_abc"],
        "language": "en",
        "schedule": "immediate",
        "timezone": "Asia/Kolkata",
    },
)
mark("create campaign", st == 200, st)
cid = camp["id"] if st == 200 else None
if cid:
    st, _ = req("POST", f"/api/v1/campaigns/{cid}/launch", {}, token=tok)
    mark("launch", st == 200, st)
    st, sim = P(f"/api/v1/campaigns/{cid}/calls/simulate", {"lead_id": "lead_abc", "outcome_hint": "Interested"})
    mark("simulate", st == 200 and (sim or {}).get("qualification", {}).get("high_intent"), st)
    if st == 200:
        call_id = sim["call"]["id"]
        st, _ = G(f"/api/v1/calls/{call_id}")
        mark("call detail", st == 200, st)
        st, _ = G(f"/api/v1/calls/{call_id}/transcript")
        mark("transcript", st == 200, st)
        st, _ = G(f"/api/v1/campaigns/{cid}")
        mark("get campaign", st == 200, st)

st, _ = req("POST", "/api/v1/saved-searches/search_001/run", {}, token=tok)
mark("radar run", st == 200, st)

for name, path in [
    ("admin users", "/api/v1/admin/users"),
    ("admin usage", "/api/v1/admin/usage"),
    ("admin audit", "/api/v1/admin/audit-logs"),
]:
    st, _ = req("GET", path, extra={"Authorization": "Bearer " + at} if at else {})
    mark(name, st == 200, st)
st, _ = G("/api/v1/admin/users")
mark("admin blocked for user", st == 403, st)

html = urllib.request.urlopen("http://localhost:5173/").read().decode()
mark("landing html", "Lumina" in html, "html")

print("PASSED", sum(1 for c in checks if c[1]), "/", len(checks))
for c in checks:
    print(("OK  " if c[1] else "FAIL"), c[0], c[2])
if any(not c[1] for c in checks):
    raise SystemExit(1)
