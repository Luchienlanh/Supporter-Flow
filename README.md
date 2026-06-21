# SupportFlow Agent

SupportFlow Agent is a portfolio MVP for a Technical Support / IT Support Engineer role. It turns developer-community questions into a structured support workflow: issue summary, category, priority, troubleshooting steps, customer-facing reply, internal notes, and a reusable knowledge base article.

It also includes a LaTeX report agent that converts an analyzed issue into a formal company-style `.tex` document for review or external handoff.

The app is intentionally scoped to the VietnamWorks JD:

- Respond to technical Q&A from GitHub, Stack Overflow, and community forums.
- Document troubleshooting steps and best practices.
- Follow a support process and produce product feedback.
- Show basic technical English writing in a support context.

## Stack

- Backend: FastAPI, SQLite, Python requests, LangChain Core workflow.
- Frontend: React, Vite, TypeScript, lucide-react.
- LLM providers:
  - NVIDIA NIM by default.
  - Ollama as local fallback.

## LangChain Workflow

The backend runs a LangChain Core workflow instead of a single LLM call:

1. `retrieve_docs`: searches seeded Developer API docs with SQLite FTS.
2. `classify_case`: creates summary, category, priority, missing info, tags, and product feedback.
3. `plan_troubleshooting`: generates reproducible diagnostic steps and escalation guidance.
4. `write_customer_reply`: drafts a concise English community-support reply.
5. `write_kb_article`: turns the case into a reusable Markdown article.
6. `validate_and_merge`: validates the output and merges it into the API response.

## LaTeX Report Agent

After a case is analyzed, SupportFlow can generate a formal issue report:

- LangChain Core workflow: `draft_report_fields -> normalize_report_fields -> render_latex_report -> save_latex_report`.
- Template file: `backend/templates/company_issue_report.tex`.
- Export folder: `exports/` (ignored by git).
- Frontend action: `Export LaTeX` downloads a `.tex` file and saves the same file on the backend.

The default template is intentionally generic so you can replace it later with a real company header, logo, footer, or document numbering format.

Compile a generated report with:

```powershell
xelatex .\exports\issue_report_case_1_20260621_130000.tex
```

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
- `POST /api/cases/{id}/latex`
- `POST /api/kb`
- `GET /api/kb`
- `GET /api/kb/{id}/markdown`

## Demo Script

1. Start backend with NIM after adding `NIM_API_KEY`, or switch to Ollama for local testing.
2. Open the frontend and run the `Authentication` sample.
3. Show summary, priority, customer reply, and troubleshooting checklist.
4. Save the generated KB article.
5. Export a LaTeX issue report from the analyzed case.
6. Paste a GitHub issue URL or Stack Overflow question URL and import it into the same support workflow.

## CV Bullet

```text
SupportFlow Agent - LangChain Technical Support Workflow
- Built a LangChain-based support workflow that classifies developer API questions, retrieves documentation, generates troubleshooting steps, drafts customer-facing English replies, validates outputs, and converts resolved issues into reusable knowledge base articles.
- Implemented FastAPI + SQLite backend, React/Vite workbench, GitHub and Stack Overflow import, seeded documentation retrieval, LaTeX issue-report export, and flexible LLM providers with NVIDIA NIM default and Ollama local fallback.
```
