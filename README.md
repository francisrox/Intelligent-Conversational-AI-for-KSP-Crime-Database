# KSP Crime AI — Intelligent Conversational AI for the KSP Crime Database

An offline-first, conversational intelligence platform for crime investigation.
Investigators ask questions in plain English and get answers, a network graph of
hidden connections, trend dashboards, explainable offender risk profiles, and
auto-generated case summaries — all running on local, free infrastructure with
no external API keys and no internet dependency at runtime.

---

## What's implemented

| Module | Status | What it does |
|---|---|---|
| Conversational Query | ✅ Full stack | Plain-English → SQL, follow-up context memory, self-correction on query errors |
| Network Analysis | ✅ Full stack | Neo4j graph; detects vehicles shared across accused in different districts |
| Trend Analytics | ✅ Full stack | Charts by crime type/district/status, monthly timeline, hotspot map |
| Offender Profiling | ✅ Full stack | Transparent weighted risk score (not a black-box model), full breakdown UI |
| Case Investigation | ✅ Full stack | LLM case summary + leads, similar-case retrieval via embedding similarity |
| Explainability | ✅ Woven throughout | Every AI output shows its evidence — SQL shown, risk factors broken down, similarity scores visible |
| Role-Based Access | ✅ Partial | JWT auth, 5 roles, 2 endpoints role-gated as proof of concept, audit logging |
| Sociological Insights | ⬜ Not built | Planned: demographic correlation, reuses the trend-aggregation pattern |
| Financial Link Analysis | ⬜ Not built | Planned: extend the Neo4j graph with account/transaction nodes |
| Forecasting | ⬜ Not built | Planned: moving-average trend flag on existing aggregation endpoints |

---

## Architecture

```
React frontend (Vite)
        │
FastAPI gateway (JWT auth, RBAC, audit log)
        │
   ┌────┴────┬──────────────┐
Query Engine  Graph Engine   Analytics Engine
(NL→SQL,      (Cypher,       (trends, risk
 Ollama LLM)   hidden links)  scoring)
        │            │              │
   PostgreSQL      Neo4j       PostgreSQL
```

**Why two databases?** Records (FIRs, accused, victims) fit SQL naturally, but
"find hidden connections across cases" is a graph-traversal problem — SQL joins
get messy fast, Neo4j makes it a straightforward Cypher query instead.

---

## Tech stack

- **Frontend:** React (Vite), Recharts, Leaflet, Cytoscape.js
- **Backend:** FastAPI (Python)
- **Databases:** PostgreSQL 16, Neo4j 5 Community
- **LLM:** Llama 3.1 8B via Ollama (local, OpenAI-compatible API, zero external cost)
- **Auth:** JWT (PyJWT) + bcrypt
- **Similarity search:** cosine similarity over Ollama embeddings (nomic-embed-text), stored in Postgres
- **Orchestration:** Docker Compose

---

## Setup

Additional detailed guides, in the order they were built:

1. This file — Phase 0 foundation (Postgres, Ollama, synthetic data)
2. [`MODULE_2_GUIDE.md`](MODULE_2_GUIDE.md) — Neo4j graph sync
3. [`MODULE_6_10_GUIDE.md`](MODULE_6_10_GUIDE.md) — embeddings, auth, RBAC

### Quick start

```bash
docker compose up -d postgres ollama neo4j
docker exec -it ksp_ollama ollama pull llama3.1:8b
docker exec -it ksp_ollama ollama pull nomic-embed-text
docker compose up -d --build backend

docker exec -it ksp_backend python data/generate_data.py
docker exec -it ksp_backend python data/sync_to_neo4j.py
Get-Content backend\data\schema_module6_10.sql | docker exec -i ksp_postgres psql -U ksp_user -d ksp_crime
docker exec -it ksp_backend python data/seed_users.py
docker exec -it ksp_backend python data/build_embeddings.py

cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

### Demo accounts

| Username | Password | Role |
|---|---|---|
| admin | admin123 | Admin |
| supervisor1 | super123 | Supervisor |
| investigator1 | invest123 | Investigator |
| analyst1 | analyst123 | Analyst |
| viewer1 | viewer123 | Viewer |

Log in as `investigator1` to see everything, then try `analyst1` and open the
Network Analysis tab — that's the live RBAC demo (access correctly denied).

---

## Known limitations

- Fully local by design — the public demo link (see submission) is a temporary
  ngrok tunnel over a laptop running the full Docker stack, not a persistent
  cloud deployment
- Only 2 of the API endpoints are currently role-gated as a proof of concept; the
  pattern (`Depends(require_role(...))`) extends to any other route in one line
- The hotspot map (Leaflet/OpenStreetMap) requires internet for map tiles even
  though the rest of the system is offline-capable
- Local 8B LLM inference on CPU takes 20–60 seconds per conversational query —
  the non-LLM endpoints (trends, network, profiles) are sub-second

---

## Links

- **Demo video:** [add link]
- **Deployed link:** [add link]
