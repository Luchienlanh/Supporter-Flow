from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from requests import HTTPError

from . import db
from .github_import import fetch_issue
from .models import (
    AnalyzeResponse,
    CaseAnalyzeRequest,
    CaseListItem,
    CaseRecord,
    GithubCaseDraft,
    GithubImportRequest,
    HealthResponse,
    KbArticle,
    SaveKbRequest,
    StackOverflowCaseDraft,
    StackOverflowImportRequest,
)
from .providers import ProviderConfigError, get_default_provider, provider_health
from .services import analyze_case
from .stackoverflow_import import fetch_question


app = FastAPI(title="SupportFlow Agent API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    db.init_db()


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        ok=True,
        default_provider=get_default_provider(),
        providers=provider_health(),
        database_path=str(db.db_path()),
    )


@app.post("/api/cases/analyze", response_model=AnalyzeResponse)
def analyze(payload: CaseAnalyzeRequest) -> AnalyzeResponse:
    try:
        case_id, _output, docs = analyze_case(payload)
    except ProviderConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPError as exc:
        detail = f"LLM provider request failed: {exc.response.status_code} {exc.response.text[:300]}"
        raise HTTPException(status_code=502, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    record = db.get_case(case_id)
    if record is None:
        raise HTTPException(status_code=500, detail="Case was analyzed but could not be loaded.")
    return AnalyzeResponse(case=record, retrieved_docs=docs)


@app.post("/api/github/import", response_model=GithubCaseDraft)
def import_github_issue(payload: GithubImportRequest) -> GithubCaseDraft:
    try:
        issue = fetch_issue(payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPError as exc:
        detail = f"GitHub request failed: {exc.response.status_code} {exc.response.text[:300]}"
        raise HTTPException(status_code=502, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return GithubCaseDraft(**issue)


@app.post("/api/stackoverflow/import", response_model=StackOverflowCaseDraft)
def import_stackoverflow_question(payload: StackOverflowImportRequest) -> StackOverflowCaseDraft:
    try:
        question = fetch_question(payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPError as exc:
        detail = f"Stack Exchange request failed: {exc.response.status_code} {exc.response.text[:300]}"
        raise HTTPException(status_code=502, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return StackOverflowCaseDraft(**question)


@app.get("/api/cases", response_model=list[CaseListItem])
def cases(limit: int = Query(default=25, ge=1, le=100)) -> list[CaseListItem]:
    return db.list_cases(limit=limit)


@app.get("/api/cases/{case_id}", response_model=CaseRecord)
def case_detail(case_id: int) -> CaseRecord:
    record = db.get_case(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return record


@app.post("/api/kb", response_model=KbArticle)
def save_kb(payload: SaveKbRequest) -> KbArticle:
    record = db.get_case(payload.case_id)
    if record is None or record.output is None:
        raise HTTPException(status_code=404, detail="Analyzed case not found.")
    markdown = payload.markdown or record.output.kb_article
    title = payload.title or _title_from_markdown(markdown) or record.title
    category = payload.category or record.category or "Other"
    return db.save_kb_article(payload.case_id, title, category, markdown)


@app.get("/api/kb", response_model=list[KbArticle])
def kb_articles(q: str = "", limit: int = Query(default=30, ge=1, le=100)) -> list[KbArticle]:
    return db.list_kb_articles(query=q, limit=limit)


@app.get("/api/kb/{article_id}/markdown", response_class=PlainTextResponse)
def kb_markdown(article_id: int) -> str:
    article = db.get_kb_article(article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Knowledge base article not found.")
    return article.markdown


def _title_from_markdown(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""
