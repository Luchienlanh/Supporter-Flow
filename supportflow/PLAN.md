# SupportFlow Agent Implementation Plan

## Summary

Build a standalone portfolio MVP for a Technical Support / IT Support Engineer role. The app handles developer API support cases from pasted text or GitHub issues, then generates support-ready outputs in English.

## Key Features

- Case intake for pasted questions, GitHub issue URLs, and Stack Overflow question URLs.
- NVIDIA NIM default LLM provider with Ollama local fallback.
- SQLite persistence for cases, agent outputs, seed docs, and saved KB articles.
- LangChain Core workflow for retrieval, classification, troubleshooting, reply drafting, KB writing, and validation.
- Separate LangChain Core LaTeX report agent for company-style issue documents.
- Seeded Developer API docs with SQLite FTS retrieval.
- React/Vite support console with provider switch, analysis output, KB preview, and LaTeX export.

## Acceptance Criteria

- Backend starts with `python -m uvicorn app.main:app --reload --port 8008`.
- Frontend starts with `npm.cmd run dev` from `supportflow/frontend`.
- NIM provider reports a clear missing-key error if `NIM_API_KEY` is absent.
- GitHub import accepts issue URLs in the form `https://github.com/{owner}/{repo}/issues/{number}`.
- Stack Overflow import accepts question URLs in the form `https://stackoverflow.com/questions/{id}/...`.
- A generated KB article can be saved.
- An analyzed case can be exported as a `.tex` issue report using `POST /api/cases/{id}/latex`.
- The LaTeX format lives in `backend/templates/company_issue_report.tex` and can be replaced with a company template later.
