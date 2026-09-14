# AI-Powered Portfolio Assistant (this chatbot)

## What it is
A Retrieval-Augmented Generation (RAG) chatbot embedded directly on
Abhijith's portfolio website, accessible via the "AI Assistant" button in
the navbar. It answers visitor questions about his background, education,
skills, and projects using only grounded, retrieved context — not made-up
or hallucinated information.

## How it works
- Frontend: a ChatGPT-style chat widget built into the portfolio site
  (HTML/CSS/JavaScript), including a message thread, typing indicator,
  and suggested-question chips.
- Voice input: visitors can also speak their question instead of typing,
  using the browser's Web Speech API, with support for English, Hindi,
  and Telugu.
- Backend: a Python FastAPI server exposing a `/api/chat` endpoint.
- Knowledge base: built by an ingestion script that pulls in three
  sources — his public GitHub repositories (README files and source
  code), a set of structured knowledge documents (profile, education,
  skills, projects, interview prep notes), and the portfolio site's own
  content.
- Retrieval: each source is split into chunks (markdown-aware, split by
  headings for cleaner topic boundaries) and embedded using OpenAI's
  `text-embedding-3-small` model into a local ChromaDB vector store.
- Generation: when a visitor asks a question, the most relevant chunks
  are retrieved from the vector store and passed as context to OpenAI's
  `gpt-4o-mini` model, which generates the final answer grounded in that
  context.

## Tech stack
Python, FastAPI, ChromaDB, OpenAI API (embeddings + GPT-4o-mini), the
GitHub REST API, HTML/CSS/JavaScript, and the browser Web Speech API for
voice input. Deployed on Render.

## Why it matters
Demonstrates a practical, end-to-end applied-AI project: data ingestion
from multiple heterogeneous sources, vector search, and grounded LLM
generation — directly relevant to data science / AI engineering roles,
and a good example of him identifying a real use case (letting recruiters
and visitors get quick, accurate answers about his work) and building a
working solution for it.
