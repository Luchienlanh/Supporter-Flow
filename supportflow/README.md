# SupportFlow Agent

SupportFlow Agent is a portfolio MVP for a Technical Support / IT Support Engineer role. It turns developer-community questions into a structured support workflow: issue summary, category, priority, troubleshooting steps, customer-facing reply, internal notes, and a reusable knowledge base article.

The app is intentionally scoped to the VietnamWorks JD:

- Respond to technical Q&A from GitHub, Stack Overflow, and community forums.
- Document troubleshooting steps and best practices.
- Follow a support process and produce product feedback.
- Show basic technical English writing in a support context.

## Stack

- Backend: FastAPI, SQLite, Python requests.
- Frontend: React, Vite, TypeScript, lucide-react.
- LLM providers:
  - NVIDIA NIM by default.
  - Ollama as local fallback.

## Run Backend

From repository root:

```powershell
cd supportflow
Copy-Item .env.example .env
```

Edit `.env` and set `NIM_API_KEY` when using NVIDIA NIM.

Run:

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8008
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8008/api/health
```

## Run Frontend

In a second terminal:

```powershell
cd supportflow/frontend
npm.cmd install
npm.cmd run dev
```

Open:

```text
http://127.0.0.1:5174
```

Vite proxies `/api` to `http://127.0.0.1:8008`.

## Provider Modes

Default NIM mode:

```powershell
$env:LLM_PROVIDER="nim"
$env:NIM_API_KEY="your_key"
python -m uvicorn app.main:app --reload --port 8008
```

Ollama mode:

```powershell
ollama pull qwen2.5-coder:7b
$env:LLM_PROVIDER="ollama"
python -m uvicorn app.main:app --reload --port 8008
```

You can also switch provider from the UI. NIM remains the default to match the implementation plan.

## API Surface

- `GET /api/health`
- `POST /api/cases/analyze`
- `POST /api/github/import`
- `POST /api/stackoverflow/import`
- `GET /api/cases`
- `GET /api/cases/{id}`
- `POST /api/kb`
- `GET /api/kb`
- `GET /api/kb/{id}/markdown`

## Demo Script

1. Start backend with NIM after adding `NIM_API_KEY`, or switch to Ollama for local testing.
2. Open the frontend and run the `Authentication` sample.
3. Show summary, priority, customer reply, and troubleshooting checklist.
4. Save the generated KB article.
5. Paste a GitHub issue URL or Stack Overflow question URL and import it into the same support workflow.

## CV Bullet

```text
SupportFlow Agent - Technical Support and Knowledge Base Assistant
- Built an AI-assisted support workflow that classifies developer API questions, generates troubleshooting steps, drafts customer-facing English replies, and converts resolved issues into reusable knowledge base articles.
- Implemented FastAPI + SQLite backend, React/Vite workbench, GitHub and Stack Overflow import, seeded documentation retrieval, and flexible LLM providers with NVIDIA NIM default and Ollama local fallback.
```
