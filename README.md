# Lumina — Illuminating the Signal

Hackathon MVP: AI sales intelligence, opportunity discovery, and demo voice qualification.

## Stack

- Frontend: React + Vite + TypeScript + Tailwind (**light mode only**)
- Backend: FastAPI + Pydantic
- Primary datastore: **SQLite** (`backend/data/sales_agent.db`)
- JSON: seed / demo / fallback only
- RAG: ChromaDB with keyword fallback
- Voice: **Demo Voice Simulation only** (no Twilio / live telephony)

## Demo accounts

| Role | Email | Password |
|---|---|---|
| User | demo@example.com | Demo123! |
| Admin | admin@example.com | Admin123! |

Seeded ABC Technologies (`lead_abc`, `opp_abc`) is labeled **DEMO DATA**.

## Run locally

```bash
# backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — Vite proxies `/api` and `/health` to port 8000.

Reset demo SQLite + reseed:

```bash
cd backend
python scripts/reset_demo.py
```

## Environment

Copy `.env.example` to `.env` (never commit `.env`).

| Variable | Purpose |
|---|---|
| `JWT_SECRET` | Replace the local default before any shared deploy |
| `AI_PROVIDER` | `demo` (default) or `openai` |
| `OPENAI_API_KEY` | Server-only. Required only for live AI |
| `OPENAI_MODEL` | Default `gpt-4o-mini` |
| `AI_BASE_URL` | Optional OpenAI-compatible base URL |
| `AI_TIMEOUT_SECONDS` | Live AI timeout |
| `URL_CACHE_TTL_SECONDS` | Website fetch cache TTL |

**Demo mode** works with no API key and no internet.

**Live AI** (`AI_PROVIDER=openai` + key): narratives/copilot may use the provider. On any failure the app falls back to deterministic Demo AI (`ai_source`: `live` \| `demo` \| `demo_fallback`).

**Website intelligence**: public HTTPS pages only, SSRF-safe. Failures return labeled DEMO fallback. Keys never go to the browser, SQLite payloads, or API responses.

## Architecture (short)

`API → store.py → SQLite` (JSON fallback if SQLite cannot start)

`get_ai()` → LiveAIProvider (optional) → DemoAIProvider

Opportunity **score** stays a local heuristic. Why Match / Why Now may cite evidence.

## Known limitations

- Voice and campaigns are simulations; live mode blocks calling
- No unrestricted web crawl; company sites only, bounded fetches
- Confidence is evidence quality, not a probability of truth
- Chroma is RAG-only, not generation
