# SupportFlow Agent Implementation Plan

## Summary

Build a standalone portfolio MVP for a Technical Support / IT Support Engineer role. The app handles developer API support cases from pasted text or GitHub issues, then generates support-ready outputs in English.

## Key Features

- Case intake for pasted questions, GitHub issue URLs, and Stack Overflow question URLs.
- NVIDIA NIM default LLM provider with Ollama and Mock alternatives.
- SQLite persistence for cases, agent outputs, seed docs, and saved KB articles.
- Seeded Developer API docs with SQLite FTS retrieval.
- React/Vite support console with provider switch, analysis output, KB preview, recent cases, and saved articles.

## Acceptance Criteria

- Backend starts with `python -m uvicorn app.main:app --reload --port 8008`.
- Frontend starts with `npm.cmd run dev` from `supportflow/frontend`.
- Mock provider can analyze a case without external keys.
- NIM provider reports a clear missing-key error if `NIM_API_KEY` is absent.
- GitHub import accepts issue URLs in the form `https://github.com/{owner}/{repo}/issues/{number}`.
- A generated KB article can be saved and listed.
