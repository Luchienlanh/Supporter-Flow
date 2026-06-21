export type ProviderName = "nim" | "ollama";

export type HealthResponse = {
  ok: boolean;
  default_provider: ProviderName;
  providers: Record<
    ProviderName,
    {
      configured: boolean;
      model: string;
      base_url: string;
    }
  >;
  database_path: string;
};

export type CaseDraft = {
  title: string;
  body: string;
  error_logs: string;
  environment: string;
  product_area: string;
  source: "paste" | "github" | "stackoverflow" | "sample";
};

export type TroubleshootingStep = {
  label: string;
  detail: string;
};

export type AgentOutput = {
  summary: string;
  category: string;
  priority: "low" | "medium" | "high" | "urgent";
  customer_reply: string;
  troubleshooting_steps: TroubleshootingStep[];
  kb_article: string;
  internal_notes: string;
  tags: string[];
  provider: string;
  model: string;
};

export type CaseRecord = {
  id: number;
  source: string;
  title: string;
  body: string;
  error_logs: string;
  environment: string;
  product_area: string;
  status: string;
  category?: string | null;
  priority?: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
  output?: AgentOutput | null;
};

export type AnalyzeResponse = {
  case: CaseRecord;
  retrieved_docs: string[];
};

export type GithubCaseDraft = {
  source: "github";
  title: string;
  body: string;
  environment: string;
  product_area: string;
  issue_url: string;
  repository: string;
  issue_number: number;
};

export type StackOverflowCaseDraft = {
  source: "stackoverflow";
  title: string;
  body: string;
  environment: string;
  product_area: string;
  question_url: string;
  question_id: number;
  tags: string[];
};

export type KbArticle = {
  id: number;
  title: string;
  category: string;
  markdown: string;
  source_case_id?: number | null;
  created_at: string;
};

export type LatexReportResponse = {
  case_id: number;
  filename: string;
  path: string;
  tex: string;
};
