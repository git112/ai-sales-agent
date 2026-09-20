# Lumina — Illuminating the Signal

Hackathon MVP: AI sales intelligence, opportunity discovery, and demo voice qualification.

## Stack

- Frontend: React + Vite + TypeScript + Tailwind (light mode only)
- Backend: FastAPI + JSON mock data
- RAG: ChromaDB with keyword fallback
- Voice: Demo / simulation only unless live providers are configured

## Demo accounts

| Role | Email | Password |
|---|---|---|
| User | demo@example.com | Demo123! |
| Admin | admin@example.com | Admin123! |

All seeded opportunities are labeled **DEMO DATA**.

## Run locally

```bash
# backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173
