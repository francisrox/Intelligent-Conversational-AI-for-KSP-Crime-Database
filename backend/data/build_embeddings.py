"""
KSP Crime AI — Build Case Embeddings (Module 6)

Embeds every crime's description text with a dedicated local embedding model,
stores the vectors in Postgres (crime_embedding table). Similar-case search is
then just an in-memory cosine-similarity scan at request time — perfectly fine
for a dataset this size (a few thousand rows), no separate vector DB needed.

Requires the embedding model pulled into Ollama first:
  docker exec -it ksp_ollama ollama pull nomic-embed-text

Run with:
  docker exec -it ksp_backend python data/build_embeddings.py

Safe to re-run — upserts by crime_id.
"""

import os
import psycopg2
from openai import OpenAI

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ksp_user:ksp_pass@localhost:5432/ksp_crime")
client = OpenAI(base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"), api_key="ollama")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT id, description FROM crime ORDER BY id")
    rows = cur.fetchall()
    print(f"Embedding {len(rows)} crime descriptions with '{EMBED_MODEL}'...")

    for i, (crime_id, description) in enumerate(rows):
        response = client.embeddings.create(model=EMBED_MODEL, input=description)
        embedding = response.data[0].embedding
        cur.execute(
            """INSERT INTO crime_embedding (crime_id, embedding) VALUES (%s, %s)
               ON CONFLICT (crime_id) DO UPDATE SET embedding = EXCLUDED.embedding""",
            (crime_id, embedding),
        )
        if (i + 1) % 100 == 0:
            conn.commit()
            print(f"  {i + 1}/{len(rows)} done")

    conn.commit()
    cur.close()
    conn.close()
    print("Done. Embeddings stored in crime_embedding.")


if __name__ == "__main__":
    main()
