# KSP Crime AI — Phase 0: Foundation

This phase sets up the environment only. No chat, no NL→SQL yet — that's Module 1, built next.

## What's in this phase

- `docker-compose.yml` — Postgres + Ollama + backend, all networked together
- `backend/data/schema.sql` — the DB schema (auto-loaded into Postgres on first boot)
- `backend/data/generate_data.py` — synthetic dataset generator (Faker)
- `backend/app/main.py` — FastAPI skeleton with two health checks (API + DB)

Stack decision: **Ollama only**, no Groq/OpenAI/Anthropic API key anywhere. Fully local,
fully free, works with the venue wifi off.

## Prerequisites

- Docker + Docker Compose installed
- ~6GB free RAM for the Ollama model once loaded (16GB machine recommended)

## Setup steps

### 1. Bring up Postgres + Ollama first (backend needs both alive)

```bash
docker compose up -d postgres ollama
```

Wait ~10s for Postgres's healthcheck to pass, then confirm the schema loaded:

```bash
docker exec -it ksp_postgres psql -U ksp_user -d ksp_crime -c "\dt"
```

You should see 7 tables: `accused`, `victim`, `crime`, `crime_accused`, `crime_victim`,
`vehicle`, `crime_vehicle`.

### 2. Pull the LLM model into the Ollama container

```bash
docker exec -it ksp_ollama ollama pull llama3.1:8b
```

This is a one-time ~4.9GB download — it's cached in the `ollama_data` Docker volume,
so you won't re-download it on every `docker compose up`.

If `llama3.1:8b` is slow on your machine, lighter alternatives are `mistral:7b` or
`qwen2.5:7b` — swap the `OLLAMA_MODEL` env var in `docker-compose.yml` and re-pull.

### 3. Bring up the backend

```bash
docker compose up -d --build backend
```

### 4. Generate the synthetic dataset

```bash
docker exec -it ksp_backend python data/generate_data.py
```

This creates:
- 300 accused (35 deliberately marked as repeat offenders, linked to 3–6 crimes each)
- 400 victims
- 150 vehicles (8 deliberately reused across crimes in *different* districts — this is
  the seeded "hidden connection" that Module 2 will surface later; it's inert for now)
- 800 crimes, spread across 5 Karnataka districts (Bengaluru, Mysuru, Mangaluru,
  Belagavi, Hubballi) and their police stations

### 5. Verify everything

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/db
```

`/health/db` should return the 7 table names and a `crime_row_count` of 800.

## Phase 0 exit criteria (don't move to Module 1 until all of these are true)

- [ ] `docker compose up -d` brings up all three containers with no errors
- [ ] `\dt` in psql shows all 7 tables
- [ ] `ollama pull` completed and `docker exec -it ksp_ollama ollama list` shows the model
- [ ] `generate_data.py` ran without errors
- [ ] `/health/db` returns `"status": "ok"` with `crime_row_count: 800`

## Resetting the database (if you change the schema)

```bash
docker compose down -v
docker compose up -d postgres ollama
# re-run generate_data.py after the backend is up again
```

## What's next

Module 1 (Conversational Interface) — NL→SQL chat endpoint, context memory for
follow-up questions, and safety guardrails on generated SQL. This will add:
`backend/app/routes/chat.py`, `backend/app/services/nl_to_sql.py`,
`backend/app/services/context_memory.py`.

Not built yet: frontend, Modules 2–10. One thing at a time.
