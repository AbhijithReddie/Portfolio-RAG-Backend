"""
main.py
=======
The RAG chat API. Run ingest.py first to build the knowledge base, then:

    uvicorn main:app --reload

This exposes POST /api/chat which the portfolio's chat widget calls.
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
import chromadb
from gemini_utils import GeminiEmbeddingFunction

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-3.6-flash")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "*")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "portfolio_knowledge"

# Retrieval is two-stage: pull a wide pool of candidates by similarity,
# then cap how many chunks can come from any single project/source so
# one repo's repeated code-file chunks can't crowd out every other
# project for broad questions like "what projects has he built?"
RAW_CANDIDATES = 40
MAX_CHUNKS_PER_SOURCE = 2
FINAL_CONTEXT_CHUNKS = 12

# Questions about "projects" should be answered from LIVE GitHub content
# (READMEs + actual code) rather than the manually-written knowledge docs
# or the static portfolio text — GitHub is the freshest, most accurate
# source for what he's actually built.
PROJECT_QUERY_KEYWORDS = (
    "project", "projects", "built", "build", "building", "repo", "repos",
    "repository", "repositories", "github", "app", "application",
    "work on", "worked on", "portfolio piece",
)

if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY is not set. Copy .env.example to .env and fill it in.")

client = genai.Client(api_key=GOOGLE_API_KEY)

app = FastAPI(title="Portfolio RAG Assistant")

origins = [o.strip() for o in FRONTEND_ORIGIN.split(",")] if FRONTEND_ORIGIN != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# Load the persisted vector store built by ingest.py
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
embed_fn = GeminiEmbeddingFunction(api_key=GOOGLE_API_KEY, model_name=EMBEDDING_MODEL)

try:
    collection = chroma_client.get_collection(name=COLLECTION_NAME, embedding_function=embed_fn)
except Exception:
    collection = None  # ingest.py hasn't been run yet


SYSTEM_PROMPT = """You are the AI assistant embedded on Sai Abhijith Reddy Chinthakuntla's \
personal portfolio website. You answer visitors' questions about his background, \
education, skills, projects, and learning goals using only the CONTEXT provided below.

Retrieval & answering rules:
- Answer ONLY using the CONTEXT. If it doesn't contain the answer, say you don't \
have that information yet, and suggest the visitor reach out directly via the \
contact section — never guess or fill gaps with assumptions.
- Do NOT invent experience, employment history, certifications, or project outcomes \
that aren't explicitly stated in the context.
- Distinguish clearly between: skills he has completed/mastered, things he is \
CURRENTLY learning, and things he is merely interested in exploring in the future. \
Don't blur these together.
- Treat project descriptions as portfolio/learning context, not proof of production \
deployment, unless the context explicitly says a project is deployed or live.
- Speak about him in the third person ("he", "his"), as his assistant — not as him.
- Keep answers simple, direct, and practical — the same style he prefers when \
explaining things himself. Prefer short paragraphs or bullet points over long \
walls of text.
- When discussing a GitHub project, mention what it does, the tech stack, and its \
repo name so the visitor could search for it.
- If the context contains MULTIPLE relevant projects/skills/items for the question \
asked, list ALL of them — don't stop after the first match you find. For "what \
projects has he built" style questions, enumerate every distinct project present \
in the context, not just one.
- For questions about his projects specifically, the context you're given comes \
directly from his live GitHub repositories (READMEs and code) — treat this as the \
most current and authoritative description of what he's actually built.
- If asked about interview-style topics (e.g. statistics), answer clearly and \
concisely as prep material, not as a lecture.
"""


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    sources: list[str] = []


def _source_key(source: str) -> str:
    """Groups a chunk's source string down to its 'project identity' so
    e.g. github_code:medworld/app.py and github_code:medworld/utils.py
    are treated as the SAME project for diversity capping, instead of
    every individual file counting as a separate source."""
    parts = source.split(":", 1)
    if len(parts) == 2 and "/" in parts[1]:
        return f"{parts[0]}:{parts[1].split('/', 1)[0]}"
    return source


def diversify_results(docs: list[str], metadatas: list[dict]) -> tuple[list[str], list[str]]:
    """Takes a wide pool of similarity-ranked candidates and returns a
    smaller, source-diverse subset — at most MAX_CHUNKS_PER_SOURCE chunks
    per project, up to FINAL_CONTEXT_CHUNKS total. Preserves the original
    relevance ordering within that constraint."""
    counts: dict[str, int] = {}
    selected_docs, selected_sources = [], []
    for doc, meta in zip(docs, metadatas):
        source = meta.get("source", "unknown")
        key = _source_key(source)
        if counts.get(key, 0) >= MAX_CHUNKS_PER_SOURCE:
            continue
        counts[key] = counts.get(key, 0) + 1
        selected_docs.append(doc)
        selected_sources.append(source)
        if len(selected_docs) >= FINAL_CONTEXT_CHUNKS:
            break
    return selected_docs, selected_sources


def is_project_query(query: str) -> bool:
    """Detects whether a question is asking about his projects — if so,
    we restrict retrieval to GitHub-sourced chunks only (see chat())."""
    q = query.lower()
    return any(kw in q for kw in PROJECT_QUERY_KEYWORDS)


@app.get("/")
def health_check():
    return {"status": "ok", "knowledge_base_ready": collection is not None}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if collection is None:
        raise HTTPException(
            status_code=503,
            detail="Knowledge base not built yet. Run `python ingest.py` on the server first.",
        )

    query = req.message.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    results = collection.query(query_texts=[query], n_results=RAW_CANDIDATES)
    raw_docs = results.get("documents", [[]])[0]
    raw_metadatas = results.get("metadatas", [[]])[0]

    if is_project_query(query):
        # Restrict to GitHub-sourced chunks (README + code) only — skip
        # the manually-written docs and portfolio text for this question
        # type, since GitHub reflects what's actually built right now.
        github_pairs = [
            (d, m) for d, m in zip(raw_docs, raw_metadatas)
            if m.get("source", "").startswith(("github_readme:", "github_code:"))
        ]
        # Safety net: if GitHub happens to have nothing relevant at all
        # (e.g. ingestion hasn't run, or a genuinely unrelated question
        # got misclassified as project-related), fall back to the full
        # pool rather than answering with zero context.
        if github_pairs:
            raw_docs, raw_metadatas = (list(x) for x in zip(*github_pairs))

    retrieved_docs, retrieved_sources = diversify_results(raw_docs, raw_metadatas)

    context = "\n\n---\n\n".join(retrieved_docs) if retrieved_docs else "No relevant context found."

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=f"CONTEXT:\n{context}\n\nVISITOR QUESTION:\n{query}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.4,
            max_output_tokens=1024,
        ),
    )

    reply = response.text
    return ChatResponse(reply=reply, sources=list(dict.fromkeys(retrieved_sources)))
