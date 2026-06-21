# SupportFlow Agent: Technical Support & Knowledge Base Assistant

## Summary
Xây một portfolio MVP trong thư mục mới `supportflow/`: một web app hỗ trợ xử lý câu hỏi kỹ thuật kiểu GitHub issue / Stack Overflow cho một sản phẩm giả lập **Developer API**. App nhận input bằng cách paste thủ công hoặc import GitHub issue, dùng LLM để phân loại vấn đề, tạo troubleshooting steps, soạn reply tiếng Anh, sinh knowledge base article Markdown, lưu case vào SQLite.

Mặc định dùng **NVIDIA NIM** qua OpenAI-compatible chat completions; hỗ trợ fallback **Ollama local** qua `/api/chat`.

## Key Changes
- Backend: Python + FastAPI + SQLite.
- Frontend: React + Vite + TypeScript, đặt riêng trong `supportflow/frontend`.
- LLM provider abstraction:
  - `LLM_PROVIDER=nim` default.
  - `NIM_BASE_URL=https://integrate.api.nvidia.com/v1`.
  - `NIM_API_KEY=<your_key>`.
  - `NIM_MODEL=nvidia/llama-3.3-nemotron-super-49b-v1.5`.
  - `OLLAMA_BASE_URL=http://localhost:11434`.
  - `OLLAMA_MODEL=qwen2.5-coder:7b`.
- GitHub import:
  - Paste issue URL dạng `https://github.com/{owner}/{repo}/issues/{number}`.
  - Backend gọi GitHub REST API để lấy issue body và comments.
  - `GITHUB_TOKEN` optional; nếu không có token thì chỉ hỗ trợ public issues và báo lỗi rõ khi rate limit/private repo.

## Core Behavior
- Input case gồm: title, body, optional error logs, environment, product area, source type.
- Agent output tiếng Anh, JSON-structured:
  - `summary`: 2-4 câu tóm tắt issue.
  - `category`: API, Auth, SDK, Database, Deployment, Billing, Bug, Usage, Other.
  - `priority`: low, medium, high, urgent.
  - `customer_reply`: câu trả lời lịch sự, actionable, không quá dài.
  - `troubleshooting_steps`: checklist từng bước.
  - `kb_article`: Markdown gồm title, symptoms, root cause, resolution, prevention.
  - `internal_notes`: giả định, missing info, suggested product feedback.
  - `tags`: 3-6 labels.
- Knowledge base seed:
  - Tạo docs giả lập cho “DevPortal API”: auth tokens, rate limits, webhook signatures, pagination, SDK install, common error codes.
  - Retrieval MVP dùng keyword/BM25 đơn giản bằng SQLite FTS5, chưa cần vector DB.
- Persistence:
  - `cases`: id, source, title, body, status, category, priority, tags_json, created_at, updated_at.
  - `case_outputs`: case_id, provider, model, summary, reply, troubleshooting_json, kb_markdown, internal_notes.
  - `kb_articles`: id, title, category, markdown, source_case_id, created_at.
  - `documents`: id, title, content, tags_json.

## API / Interfaces
- `GET /api/health`: provider config visibility without secrets.
- `POST /api/cases/analyze`: accepts pasted support case and returns full agent output.
- `POST /api/github/import`: accepts GitHub issue URL, returns normalized case draft.
- `GET /api/cases`: list saved cases with filters category/priority/source.
- `GET /api/cases/{id}`: case detail + generated output.
- `POST /api/kb`: save generated KB article from a case.
- `GET /api/kb`: list/search KB articles.
- `GET /api/kb/{id}/markdown`: return Markdown for copy/export.

## Frontend
- First screen is the actual workbench, not a landing page.
- Layout:
  - Left panel: source selector tabs `Paste` / `GitHub`, case input, provider status.
  - Center panel: generated support reply and troubleshooting checklist.
  - Right panel: KB article preview, internal notes, tags, priority/category.
  - Bottom/table view: recent cases and saved KB articles.
- Controls:
  - Buttons with lucide icons: Analyze, Import, Save KB, Copy Reply, Copy Markdown.
  - Segmented control for provider: NIM / Ollama / Mock, with NIM selected by default.
  - Status badge for provider health and missing API key.
- Include 3 sample templates:
  - `401 Unauthorized with valid token`
  - `Webhook signature mismatch`
  - `SDK install fails on Windows`

## Implementation Steps
1. Scaffold `supportflow/` with `backend/`, `frontend/`, `data/seed_docs/`, `README.md`, `.env.example`.
2. Backend:
   - Add FastAPI app, Pydantic request/response models, SQLite init, repository layer.
   - Implement `LLMClient` interface with `NimClient`, `OllamaClient`, `MockClient`.
   - Implement prompt builder with strict JSON response instructions and fallback JSON repair.
   - Implement GitHub issue URL parser and issue/comments fetcher.
   - Implement SQLite FTS5 retrieval over seed docs.
3. Frontend:
   - Create Vite React app with TypeScript.
   - Build workbench UI and service layer for API calls.
   - Add loading, error, empty, copied, provider-missing-key states.
4. Demo data:
   - Seed 6-8 Developer API docs.
   - Seed 3 example cases for quick demo.
5. Documentation:
   - README with setup for NIM and Ollama.
   - Add CV bullet and demo script:
     - “Built an AI-assisted support workflow that classifies technical questions, drafts customer-facing replies, generates troubleshooting steps, and converts resolved issues into reusable knowledge base articles.”

## Test Plan
- Backend tests:
  - Provider selection chooses NIM by default.
  - Missing `NIM_API_KEY` returns clear configuration error, not a crash.
  - Ollama client calls `/api/chat` with `stream=false`.
  - GitHub URL parser handles valid/invalid issue URLs.
  - Analyzer stores case + output in SQLite.
  - KB save creates Markdown article linked to source case.
- Frontend checks:
  - TypeScript build passes.
  - Analyze flow renders summary, reply, steps, KB preview.
  - GitHub import error state is visible and useful.
  - Copy buttons copy correct text.
- Manual acceptance:
  - Run backend and frontend locally.
  - Analyze all 3 sample cases.
  - Save at least 1 KB article.
  - Switch provider to Ollama and confirm graceful behavior if Ollama is offline.

## Assumptions
- Project name: `SupportFlow Agent`.
- Scope: portfolio MVP, not production helpdesk.
- Placement: new standalone folder `supportflow/`.
- Domain: fake Developer API support.
- Input: both paste and GitHub issue import.
- Output language: English.
- NIM default uses NVIDIA’s OpenAI-compatible chat completions endpoint documented at `https://integrate.api.nvidia.com/v1/chat/completions`.
- Ollama fallback uses official local chat endpoint `POST /api/chat`.
- GitHub import uses GitHub REST issue and issue comments endpoints.

References:
- NVIDIA NIM API reference: https://docs.api.nvidia.com/nim/reference/nvidia-llama-3_3-nemotron-super-49b-v1-infer
- Ollama API docs: https://github.com/ollama/ollama/blob/main/docs/api.md
- GitHub Issues REST API: https://docs.github.com/en/rest/issues/issues
- GitHub Issue Comments REST API: https://docs.github.com/en/rest/issues/comments
