import type {
  AnalyzeResponse,
  CaseDraft,
  CaseRecord,
  GithubCaseDraft,
  HealthResponse,
  KbArticle,
  LatexReportResponse,
  ProviderName,
  StackOverflowCaseDraft,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = typeof payload.detail === "string" ? payload.detail : "Request failed.";
    throw new Error(message);
  }
  return payload as T;
}

export function getHealth() {
  return request<HealthResponse>("/api/health");
}

export function analyzeCase(draft: CaseDraft, provider: ProviderName) {
  return request<AnalyzeResponse>("/api/cases/analyze", {
    method: "POST",
    body: JSON.stringify({ ...draft, provider }),
  });
}

export function importGithubIssue(url: string) {
  return request<GithubCaseDraft>("/api/github/import", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export function importStackOverflowQuestion(url: string) {
  return request<StackOverflowCaseDraft>("/api/stackoverflow/import", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export function listCases() {
  return request<CaseRecord[]>("/api/cases?limit=12");
}

export function listKbArticles() {
  return request<KbArticle[]>("/api/kb?limit=12");
}

export function saveKbArticle(caseId: number, markdown: string) {
  return request<KbArticle>("/api/kb", {
    method: "POST",
    body: JSON.stringify({ case_id: caseId, markdown }),
  });
}

export function generateLatexReport(caseId: number, provider: ProviderName) {
  return request<LatexReportResponse>(`/api/cases/${caseId}/latex`, {
    method: "POST",
    body: JSON.stringify({ provider }),
  });
}
