import os
from openai import OpenAI

client = OpenAI(base_url=os.getenv("OLLAMA_BASE_URL"), api_key="ollama")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def get_embedding(text: str):
    response = client.embeddings.create(model=EMBED_MODEL, input=text)
    return response.data[0].embedding
