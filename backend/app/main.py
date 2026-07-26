from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db import get_connection
from app.graph_db import run_cypher
from app.routes import chat, network, auth, investigate, trends, profile

app = FastAPI(title="KSP Crime AI - Backend", version="0.1.0")

# Frontend runs on a different port (Vite dev server) — needs CORS to call this API.
# Locked to localhost dev ports only; tighten further before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/chat")
app.include_router(network.router, prefix="/api/network")
app.include_router(auth.router, prefix="/api/auth")
app.include_router(investigate.router, prefix="/api/investigate")
app.include_router(trends.router, prefix="/api/trends")
app.include_router(profile.router, prefix="/api/profile")


@app.get("/health")
def health():
    """Basic liveness check for the API itself."""
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    """Confirms Postgres is reachable and the schema has loaded (Phase 0 gate)."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
        )
        tables = [row[0] for row in cur.fetchall()]
        cur.execute("SELECT COUNT(*) FROM crime")
        crime_count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return {"status": "ok", "tables": tables, "crime_row_count": crime_count}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/health/graph")
def health_graph():
    """Confirms Neo4j is reachable and the graph has been synced (Module 2 gate)."""
    try:
        node_counts = [
            dict(r) for r in run_cypher(
                "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY label"
            )
        ]
        rel_counts = [
            dict(r) for r in run_cypher(
                "MATCH ()-[r]->() RETURN type(r) AS rel_type, count(*) AS count ORDER BY rel_type"
            )
        ]
        return {"status": "ok", "node_counts": node_counts, "relationship_counts": rel_counts}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
