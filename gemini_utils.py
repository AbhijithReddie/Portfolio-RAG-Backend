"""
gemini_utils.py
================
Shared embedding function so ingest.py (writing to the vector store) and
main.py (querying it) use the exact same embedding model and settings —
they must match, or retrieval quality silently breaks.

Uses Google's official "Google Gen AI SDK" (`google-genai` package),
Google's current recommended SDK for the Gemini API.
"""

from google import genai
from chromadb import Documents, EmbeddingFunction, Embeddings


class GeminiEmbeddingFunction(EmbeddingFunction):
    """A ChromaDB-compatible embedding function backed by Gemini's
    embedding model (gemini-embedding-001, free via Google AI Studio)."""

    def __init__(self, api_key: str, model_name: str = "gemini-embedding-001"):
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set. Copy .env.example to .env and fill it in.")
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        result = self.client.models.embed_content(model=self.model_name, contents=input)
        return [e.values for e in result.embeddings]
