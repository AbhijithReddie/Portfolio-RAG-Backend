# RAG Knowledge Base Guidance

## Purpose
This document is intended to help a Retrieval-Augmented Generation (RAG) system answer questions about the user's professional background, technical skills, projects, learning goals and preferred communication style.

## Retrieval Rules
When answering a question about the user:
- Prefer the most specific document/chunk available.
- Do not invent experience, employment, certifications or project outcomes.
- Distinguish between completed skills, current learning, and future interests.
- Treat project descriptions as portfolio context, not proof of production deployment unless explicitly stated.
- Use the user's preferred simple and practical communication style for explanations.

## Useful Retrieval Categories
- `profile`: identity-neutral professional profile and communication preferences
- `career`: education, certifications, career direction and job interests
- `technical`: programming, data, cloud, DevOps and GenAI skills
- `projects`: project names, architectures, goals and implementation details
- `statistics`: statistics interview preparation
- `rag`: information about how this knowledge base should be interpreted

## Example Queries
- What technologies does Abhijith know?
- What is Abhijith's career goal?
- Which AWS certification does he have?
- What projects has he built?
- What is the AI-Powered Portfolio Assistant?
- What is MedWorld?
- What is the Accident Analysis project?
- What is his preferred interview-answer format?
- What statistics topics is he preparing for?
- What GenAI topics is he learning?
- What skills is he developing for DevOps?
