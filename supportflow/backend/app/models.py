from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ProviderName = Literal["nim", "ollama"]


class CaseAnalyzeRequest(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    body: str = Field(min_length=5)
    error_logs: str = ""
    environment: str = ""
    product_area: str = ""
    source: Literal["paste", "github", "stackoverflow", "sample"] = "paste"
    provider: ProviderName | None = None


class GithubImportRequest(BaseModel):
    url: str = Field(min_length=10)


class GithubCaseDraft(BaseModel):
    source: Literal["github"] = "github"
    title: str
    body: str
    environment: str = ""
    product_area: str = "Developer API"
    issue_url: str
    repository: str
    issue_number: int


class StackOverflowImportRequest(BaseModel):
    url: str = Field(min_length=10)


class StackOverflowCaseDraft(BaseModel):
    source: Literal["stackoverflow"] = "stackoverflow"
    title: str
    body: str
    environment: str = ""
    product_area: str = "Stack Overflow Q&A"
    question_url: str
    question_id: int
    tags: list[str] = []


class TroubleshootingStep(BaseModel):
    label: str
    detail: str = ""


class AgentOutput(BaseModel):
    summary: str
    category: str
    priority: Literal["low", "medium", "high", "urgent"]
    customer_reply: str
    troubleshooting_steps: list[TroubleshootingStep]
    kb_article: str
    internal_notes: str
    tags: list[str]
    provider: str
    model: str


class CaseRecord(BaseModel):
    id: int
    source: str
    title: str
    body: str
    environment: str
    product_area: str
    status: str
    category: str | None = None
    priority: str | None = None
    tags: list[str] = []
    created_at: str
    updated_at: str
    output: AgentOutput | None = None


class CaseListItem(BaseModel):
    id: int
    title: str
    source: str
    status: str
    category: str | None = None
    priority: str | None = None
    tags: list[str] = []
    created_at: str
    updated_at: str


class AnalyzeResponse(BaseModel):
    case: CaseRecord
    retrieved_docs: list[str]


class SaveKbRequest(BaseModel):
    case_id: int
    title: str | None = None
    category: str | None = None
    markdown: str | None = None


class KbArticle(BaseModel):
    id: int
    title: str
    category: str
    markdown: str
    source_case_id: int | None = None
    created_at: str


class HealthResponse(BaseModel):
    ok: bool
    default_provider: str
    providers: dict[str, dict[str, object]]
    database_path: str
