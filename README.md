# Portfolio RAG Assistant — Backend

A small FastAPI backend that answers questions about Abhijith using
Retrieval-Augmented Generation (RAG): his GitHub repos, his portfolio
content, and his knowledge base documents are embedded into a local
vector store, retrieved per question, and fed to Google's Gemini
(`gemini-2.5-flash`) to generate grounded answers.

Uses **Google Gemini** — free via Google AI Studio, no credit card required.

## 1. Local setup

```bash
cd rag-backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then open .env and paste in your real GOOGLE_API_KEY
```

Get a free API key at **https://aistudio.google.com/apikey** — sign in
with a Google account, click "Create API key". No billing setup needed
to use the Flash models this project relies on.

## 2. Your knowledge base documents (already included)

The `documents/` folder already contains a full knowledge base covering:
profile, education & career, technical skills, projects (including ones not
yet on the public site), statistics interview prep, and retrieval guidance
for how the assistant should reason about all of it.

Add or edit any `.md`/`.txt`/`.pdf`/`.docx` file in there any time — nothing
else needs to change.

## 3. Build the knowledge base

This step fetches your GitHub repos, reads `documents/`, and embeds
everything into a local vector store (`chroma_db/`).

```bash
python ingest.py
```

Re-run this any time you:
- push a new GitHub repo or update an existing one
- add/change a file in `documents/`
- edit the `portfolio_content()` section in `ingest.py`

## 4. Run the server locally

```bash
uvicorn main:app --reload
```

Visit `http://localhost:8000` — you should see `{"status":"ok", ...}`.
Test the chat endpoint:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What projects has he built?"}'
```

## 5. Deploy to Render (recommended, free tier)

1. Push this `rag-backend` folder to a GitHub repo.
2. Go to [render.com](https://render.com) → **New +** → **Blueprint**,
   and point it at your repo (it will read `render.yaml` automatically).
3. When prompted, fill in the environment variables:
   - `GOOGLE_API_KEY` — your real Gemini API key
   - `FRONTEND_ORIGIN` — your deployed portfolio's URL (e.g.
     `https://abhijithreddie.github.io`), so only your site can call this API
   - `GITHUB_TOKEN` — optional, but recommended (raises GitHub API rate limits)
4. Render will run `pip install` + `python ingest.py` automatically on
   every deploy (see `buildCommand` in `render.yaml`), then start the
   server. First build may take a minute or two while it embeds everything.
5. Once deployed, copy your service's URL — it'll look like
   `https://portfolio-rag-backend.onrender.com`.

## 6. Point the frontend at your deployed backend

In `index.html`, find this line near the top of the chatbot `<script>`:

```js
const BACKEND_URL = "https://your-backend-url.onrender.com/api/chat";
```

Replace it with your real Render URL, then redeploy your portfolio site.

## Notes on cost

- `gemini-embedding-001` and `gemini-2.5-flash` are both available on
  Gemini's **free tier** through Google AI Studio — no credit card
  needed to get started. Free-tier daily/per-minute request limits are
  more than enough for a portfolio-scale project.
- If you ever outgrow the free tier (very unlikely for a portfolio site),
  Gemini's paid pricing is still inexpensive — see
  ai.google.dev/pricing for current rates.
- Render's free tier spins the service down after inactivity; the first
  request after idle time takes ~30-50 seconds to "wake up." This is
  normal — a small "waking up the assistant..." message in the frontend
  can smooth this over (already included).
