"""
ingest.py
=========
Builds (or rebuilds) the RAG knowledge base used by main.py.

Pulls content from THREE sources:
  1. Local files dropped into ./documents  (resume, PDFs, .docx, .txt, .md)
  2. Your public GitHub repos               (README + source code files)
  3. This portfolio site's own content       (hardcoded below — edit freely)

Each source is split into overlapping text chunks, embedded with Google's
embedding model, and stored in a local ChromaDB collection on disk
(./chroma_db). main.py reads from that same folder at query time.

Run this:
  - once, right after you set up the project
  - again, any time you add a new document, push a new repo, or change
    the portfolio content below

    python ingest.py
"""

import os
import glob
import re
import time
from dotenv import load_dotenv
import requests
import chromadb
from pypdf import PdfReader
from docx import Document as DocxDocument
from gemini_utils import GeminiEmbeddingFunction

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "AbhijithReddie")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")

DOCUMENTS_DIR = os.path.join(os.path.dirname(__file__), "documents")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "portfolio_knowledge"

# File types worth pulling from each repo. Keep this list short — the goal
# is to explain WHAT the project does and HOW, not to embed every file.
CODE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".ipynb", ".md"}
MAX_FILE_CHARS = 8000       # skip/trim huge files (e.g. generated notebooks)
MAX_FILES_PER_REPO = 12     # keep ingestion fast and cheap


# ---------------------------------------------------------------------------
# 1. LOCAL DOCUMENTS  (resume, PDFs, .docx, .txt, .md dropped in ./documents)
# ---------------------------------------------------------------------------
def chunk_markdown(text, source, max_chunk=800, overlap=100):
    """Splits markdown by headings (#, ##, ###) into semantic sections first —
    much cleaner for retrieval than blind character windows, since each
    chunk stays topically coherent (e.g. one Q&A item, one project). Falls
    back to the sliding-window chunker only for oversized sections."""
    sections = re.split(r'\n(?=#{1,3}\s)', text.strip())
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        if len(section) <= max_chunk:
            chunks.append({"text": section, "source": source})
        else:
            chunks.extend(chunk_text(section, source=source, chunk_size=max_chunk, overlap=overlap))
    return chunks


def load_local_documents():
    chunks = []
    if not os.path.isdir(DOCUMENTS_DIR):
        return chunks

    for path in glob.glob(os.path.join(DOCUMENTS_DIR, "**/*"), recursive=True):
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(path)[1].lower()
        name = os.path.basename(path)
        try:
            if ext == ".pdf":
                text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
            elif ext == ".docx":
                text = "\n".join(p.text for p in DocxDocument(path).paragraphs)
            elif ext in (".txt", ".md"):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            else:
                continue
        except Exception as e:
            print(f"  [!] Skipped {name}: {e}")
            continue

        if text.strip():
            print(f"  + Loaded document: {name} ({len(text)} chars)")
            if ext == ".md":
                chunks.extend(chunk_markdown(text, source=f"document:{name}"))
            else:
                chunks.extend(chunk_text(text, source=f"document:{name}"))
    return chunks


# ---------------------------------------------------------------------------
# 2. GITHUB REPOS  (README + key source files, via GitHub's public REST API)
# ---------------------------------------------------------------------------
def github_headers():
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def fetch_github_repos():
    chunks = []
    print(f"\nFetching public repos for GitHub user: {GITHUB_USERNAME}")
    resp = requests.get(
        f"https://api.github.com/users/{GITHUB_USERNAME}/repos",
        headers=github_headers(),
        params={"per_page": 100, "sort": "updated"},
    )
    if resp.status_code != 200:
        print(f"  [!] Could not fetch repo list ({resp.status_code}): {resp.text[:200]}")
        return chunks

    repos = [r for r in resp.json() if not r.get("fork")]
    print(f"  Found {len(repos)} repos")

    for repo in repos:
        repo_name = repo["name"]
        default_branch = repo.get("default_branch", "main")
        print(f"  - {repo_name}")

        # README (GitHub has a dedicated endpoint that returns rendered/raw text)
        readme_resp = requests.get(
            f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/readme",
            headers={**github_headers(), "Accept": "application/vnd.github.raw+json"},
        )
        if readme_resp.status_code == 200 and readme_resp.text.strip():
            text = f"Project: {repo_name}\nDescription: {repo.get('description') or 'N/A'}\n\n{readme_resp.text}"
            chunks.extend(chunk_markdown(text, source=f"github_readme:{repo_name}"))

        # Source files (walk the repo tree, filter by extension, cap count/size)
        tree_resp = requests.get(
            f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/git/trees/{default_branch}",
            headers=github_headers(),
            params={"recursive": "1"},
        )
        if tree_resp.status_code != 200:
            continue

        files = [
            item for item in tree_resp.json().get("tree", [])
            if item["type"] == "blob"
            and os.path.splitext(item["path"])[1].lower() in CODE_EXTENSIONS
        ][:MAX_FILES_PER_REPO]

        for item in files:
            raw_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{repo_name}/{default_branch}/{item['path']}"
            file_resp = requests.get(raw_url)
            if file_resp.status_code != 200:
                continue
            content = file_resp.text[:MAX_FILE_CHARS]
            if content.strip():
                text = f"Project: {repo_name}\nFile: {item['path']}\n\n{content}"
                chunks.extend(chunk_text(text, source=f"github_code:{repo_name}/{item['path']}"))

        time.sleep(0.2)  # be polite to the API / avoid rate limits

    return chunks


# ---------------------------------------------------------------------------
# 3. PORTFOLIO CONTENT  (edit this dict whenever the site copy changes)
# ---------------------------------------------------------------------------
def portfolio_content():
    sections = {
        "about": (
            "Sai Abhijith Reddy Chinthakuntla is a Computer Science graduate and "
            "aspiring Data Scientist with a strong interest in turning data into "
            "meaningful insights and practical solutions. He enjoys working with "
            "Python, SQL, data analytics, machine learning, and data visualization. "
            "He is currently pursuing a Data Analytics & Data Science course at "
            "Imarticus Learning, Hyderabad."
        ),
        "education": (
            "Bachelor of Technology in Computer Science & Engineering from CVR "
            "College of Engineering, Hyderabad. He is also currently enrolled in a "
            "Data Analytics & Data Science program at Imarticus Learning, Hyderabad, "
            "covering statistics, Python for data science, SQL, machine learning, "
            "and business analytics."
        ),
        "skills": (
            "His core skills include Python, SQL, Machine Learning, Data Analytics, "
            "Data Visualization, JavaScript, Java, Statistics, Git & GitHub, and "
            "Excel / Power BI."
        ),
        "status": (
            "He is currently open to Data Analyst and Data Science roles. He is "
            "based in Hyderabad, Telangana, India."
        ),
        "contact": (
            "You can contact him at abhijithreddychinthakuntla@gmail.com, connect "
            "on LinkedIn at linkedin.com/in/abhijithreddych, or view his work on "
            "GitHub at github.com/AbhijithReddie."
        ),
    }
    chunks = []
    for name, text in sections.items():
        chunks.extend(chunk_text(text, source=f"portfolio:{name}"))
    return chunks


# ---------------------------------------------------------------------------
# Chunking helper
# ---------------------------------------------------------------------------
def chunk_text(text, source, chunk_size=800, overlap=100):
    """Simple sliding-window character chunker. Good enough for this scale;
    swap for a token-aware splitter (e.g. tiktoken-based) if you outgrow it."""
    text = text.strip()
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        piece = text[start:end].strip()
        if piece:
            chunks.append({"text": piece, "source": source})
        start += chunk_size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Build the vector store
# ---------------------------------------------------------------------------
def embed_batch_with_retry(collection, batch, ids, max_retries=6):
    """Adds a batch to the collection, automatically waiting and retrying
    if Gemini's free-tier rate limit is hit (HTTP 429). Reads the
    suggested wait time out of the error message when available."""
    for attempt in range(max_retries):
        try:
            collection.add(
                documents=[c["text"] for c in batch],
                metadatas=[{"source": c["source"]} for c in batch],
                ids=ids,
            )
            return
        except Exception as e:
            msg = str(e)
            if "429" not in msg and "RESOURCE_EXHAUSTED" not in msg:
                raise  # not a rate-limit error — don't swallow real bugs
            match = re.search(r"retry in ([\d.]+)s", msg)
            wait = float(match.group(1)) + 3 if match else 20 * (attempt + 1)
            print(f"  Rate limited — waiting {wait:.0f}s before retrying (attempt {attempt + 1}/{max_retries})...")
            time.sleep(wait)
    raise RuntimeError("Still rate-limited after several retries. Wait a minute and re-run python ingest.py.")


def build_vectorstore(all_chunks):
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not set. Copy .env.example to .env and fill it in.")

    print(f"\nEmbedding {len(all_chunks)} chunks with {EMBEDDING_MODEL} (Gemini)...")
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Start clean each run so stale/removed content doesn't linger
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    embed_fn = GeminiEmbeddingFunction(api_key=GOOGLE_API_KEY, model_name=EMBEDDING_MODEL)
    collection = client.create_collection(name=COLLECTION_NAME, embedding_function=embed_fn)

    # Small batches + a pause between them keeps us comfortably under
    # Gemini's free-tier "100 embedding requests/minute" limit. The
    # retry logic above is a safety net if we still get rate-limited.
    batch_size = 10
    pause_seconds = 8
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        ids = [f"chunk-{i + j}" for j in range(len(batch))]
        embed_batch_with_retry(collection, batch, ids)
        print(f"  Embedded {min(i + batch_size, len(all_chunks))}/{len(all_chunks)}")
        time.sleep(pause_seconds)

    print(f"\nDone. Vector store saved to: {CHROMA_DIR}")


if __name__ == "__main__":
    print("=" * 60)
    print("Building portfolio RAG knowledge base")
    print("=" * 60)

    all_chunks = []
    print("\n[1/3] Local documents (./documents)")
    all_chunks += load_local_documents()

    print("\n[2/3] GitHub repos")
    all_chunks += fetch_github_repos()

    print("\n[3/3] Portfolio content")
    all_chunks += portfolio_content()

    if not all_chunks:
        print("\nNo content found anywhere — check your sources.")
    else:
        build_vectorstore(all_chunks)