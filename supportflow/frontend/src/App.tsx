import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  BookOpen,
  Check,
  Clipboard,
  DownloadCloud,
  FileDown,
  FileText,
  Github,
  Loader2,
  MessagesSquare,
  MessageSquareText,
  Play,
  Save,
  Server,
  Sparkles,
} from "lucide-react";
import {
  analyzeCase,
  generateLatexReport,
  getHealth,
  importGithubIssue,
  importStackOverflowQuestion,
  saveKbArticle,
} from "./api";
import type {
  AnalyzeResponse,
  CaseDraft,
  HealthResponse,
  LatexReportResponse,
  ProviderName,
} from "./types";

const emptyDraft: CaseDraft = {
  title: "",
  body: "",
  error_logs: "",
  environment: "",
  product_area: "Developer API",
  source: "paste",
};

const samples: CaseDraft[] = [
  {
    title: "401 Unauthorized even though the token was just generated",
    body: "I generated a new API token from the dashboard. GET /v1/account still returns 401. This happens in production only.",
    error_logs: "HTTP/1.1 401 Unauthorized\n{\"error\":{\"code\":\"unauthorized\",\"message\":\"Invalid token\",\"request_id\":\"req_prod_8a91\"}}",
    environment: "Node.js 20, production base URL",
    product_area: "Authentication",
    source: "sample",
  },
  {
    title: "Webhook signature mismatch after moving behind a proxy",
    body: "Webhook verification worked locally, but after deploying behind our proxy every event fails signature verification.",
    error_logs: "signature_mismatch for event evt_2091",
    environment: "Express app behind reverse proxy",
    product_area: "Webhooks",
    source: "sample",
  },
  {
    title: "Windows install fails for the Node SDK",
    body: "npm install @devportal/sdk fails on a Windows laptop used by our support team.",
    error_logs: "npm ERR! code ECONNRESET",
    environment: "Windows 11, Node.js 18, corporate proxy",
    product_area: "SDK",
    source: "sample",
  },
];

const providerLabels: Record<ProviderName, string> = {
  nim: "NIM",
  ollama: "Ollama",
};

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [provider, setProvider] = useState<ProviderName>("nim");
  const [activeSource, setActiveSource] = useState<"paste" | "github" | "stackoverflow">("paste");
  const [draft, setDraft] = useState<CaseDraft>(samples[0]);
  const [issueUrl, setIssueUrl] = useState("");
  const [stackOverflowUrl, setStackOverflowUrl] = useState("");
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [latexReport, setLatexReport] = useState<LatexReportResponse | null>(null);
  const [busy, setBusy] = useState<"analyze" | "github" | "stackoverflow" | "save" | "latex" | "boot" | null>("boot");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState("");

  useEffect(() => {
    void bootstrap();
  }, []);

  const selectedProvider = health?.providers?.[provider];
  const canAnalyze = draft.title.trim().length > 2 && draft.body.trim().length > 4 && !busy;
  const currentOutput = result?.case.output ?? null;

  const priorityClass = useMemo(() => {
    const priority = currentOutput?.priority ?? result?.case.priority ?? "medium";
    return `priority priority-${priority}`;
  }, [currentOutput?.priority, result?.case.priority]);

  async function bootstrap() {
    setBusy("boot");
    setError("");
    try {
      const nextHealth = await getHealth();
      setHealth(nextHealth);
      setProvider(nextHealth.default_provider);
    } catch (bootError) {
      setError(errorMessage(bootError));
    } finally {
      setBusy(null);
    }
  }

  async function handleAnalyze() {
    if (!canAnalyze) {
      return;
    }
    setBusy("analyze");
    setError("");
    setResult(null);
    setLatexReport(null);
    try {
      const nextResult = await analyzeCase(draft, provider);
      setResult(nextResult);
    } catch (analyzeError) {
      setError(errorMessage(analyzeError));
    } finally {
      setBusy(null);
    }
  }

  async function handleGithubImport() {
    if (!issueUrl.trim() || busy) {
      return;
    }
    setBusy("github");
    setError("");
    try {
      const imported = await importGithubIssue(issueUrl.trim());
      setDraft({
        title: imported.title,
        body: imported.body,
        error_logs: "",
        environment: imported.environment,
        product_area: imported.product_area,
        source: imported.source,
      });
      setActiveSource("paste");
    } catch (githubError) {
      setError(errorMessage(githubError));
    } finally {
      setBusy(null);
    }
  }

  async function handleStackOverflowImport() {
    if (!stackOverflowUrl.trim() || busy) {
      return;
    }
    setBusy("stackoverflow");
    setError("");
    try {
      const imported = await importStackOverflowQuestion(stackOverflowUrl.trim());
      setDraft({
        title: imported.title,
        body: imported.body,
        error_logs: "",
        environment: imported.environment,
        product_area: imported.product_area,
        source: imported.source,
      });
      setActiveSource("paste");
    } catch (stackOverflowError) {
      setError(errorMessage(stackOverflowError));
    } finally {
      setBusy(null);
    }
  }

  async function handleSaveKb() {
    if (!result?.case.id || !currentOutput || busy) {
      return;
    }
    setBusy("save");
    setError("");
    try {
      await saveKbArticle(result.case.id, currentOutput.kb_article);
    } catch (saveError) {
      setError(errorMessage(saveError));
    } finally {
      setBusy(null);
    }
  }

  async function handleGenerateLatex() {
    if (!result?.case.id || !currentOutput || busy) {
      return;
    }
    setBusy("latex");
    setError("");
    try {
      const report = await generateLatexReport(result.case.id, provider);
      setLatexReport(report);
      downloadTexFile(report);
    } catch (latexError) {
      setError(errorMessage(latexError));
    } finally {
      setBusy(null);
    }
  }

  async function copyText(label: string, value: string) {
    await navigator.clipboard.writeText(value);
    setCopied(label);
    window.setTimeout(() => setCopied(""), 1400);
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="kicker">SupportFlow Agent</p>
          <h1>Developer API support console</h1>
        </div>
        <div className="topbar-actions">
          <div className="provider-switch" aria-label="LLM provider">
            {(Object.keys(providerLabels) as ProviderName[]).map((item) => (
              <button
                className={provider === item ? "active" : ""}
                key={item}
                onClick={() => setProvider(item)}
                type="button"
              >
                {providerLabels[item]}
              </button>
            ))}
          </div>
          <div className={`health-pill ${selectedProvider?.configured ? "ok" : "warn"}`}>
            <Server size={16} />
            <span>{selectedProvider?.configured ? selectedProvider.model : "Key required"}</span>
          </div>
        </div>
      </header>

      {error ? (
        <section className="error-strip">
          <AlertCircle size={18} />
          <span>{error}</span>
        </section>
      ) : null}

      <section className="workspace">
        <aside className="panel intake-panel">
          <div className="panel-title">
            <div>
              <span>Case intake</span>
              <strong>
                {draft.source === "github"
                  ? "GitHub issue"
                  : draft.source === "stackoverflow"
                    ? "Stack Overflow question"
                    : "Manual case"}
              </strong>
            </div>
            <FileText size={20} />
          </div>

          <div className="source-tabs">
            <button
              className={activeSource === "paste" ? "active" : ""}
              onClick={() => setActiveSource("paste")}
              type="button"
            >
              <Clipboard size={16} />
              Paste
            </button>
            <button
              className={activeSource === "github" ? "active" : ""}
              onClick={() => setActiveSource("github")}
              type="button"
            >
              <Github size={16} />
              GitHub
            </button>
            <button
              className={activeSource === "stackoverflow" ? "active" : ""}
              onClick={() => setActiveSource("stackoverflow")}
              type="button"
            >
              <MessagesSquare size={16} />
              Stack Overflow
            </button>
          </div>

          {activeSource === "github" ? (
            <div className="github-import">
              <label>
                Issue URL
                <input
                  onChange={(event) => setIssueUrl(event.target.value)}
                  placeholder="https://github.com/owner/repo/issues/123"
                  value={issueUrl}
                />
              </label>
              <button className="secondary-button" disabled={!issueUrl.trim() || !!busy} onClick={handleGithubImport} type="button">
                {busy === "github" ? <Loader2 className="spin" size={17} /> : <DownloadCloud size={17} />}
                Import issue
              </button>
            </div>
          ) : null}

          {activeSource === "stackoverflow" ? (
            <div className="github-import">
              <label>
                Question URL
                <input
                  onChange={(event) => setStackOverflowUrl(event.target.value)}
                  placeholder="https://stackoverflow.com/questions/123/title"
                  value={stackOverflowUrl}
                />
              </label>
              <button className="secondary-button" disabled={!stackOverflowUrl.trim() || !!busy} onClick={handleStackOverflowImport} type="button">
                {busy === "stackoverflow" ? <Loader2 className="spin" size={17} /> : <DownloadCloud size={17} />}
                Import question
              </button>
            </div>
          ) : null}

          <label>
            Title
            <input
              onChange={(event) => setDraft({ ...draft, title: event.target.value, source: "paste" })}
              placeholder="401 Unauthorized with valid token"
              value={draft.title}
            />
          </label>

          <label>
            Body
            <textarea
              className="case-body"
              onChange={(event) => setDraft({ ...draft, body: event.target.value, source: "paste" })}
              value={draft.body}
            />
          </label>

          <div className="field-grid">
            <label>
              Product area
              <input
                onChange={(event) => setDraft({ ...draft, product_area: event.target.value })}
                value={draft.product_area}
              />
            </label>
            <label>
              Environment
              <input
                onChange={(event) => setDraft({ ...draft, environment: event.target.value })}
                placeholder="Node 20, Windows 11"
                value={draft.environment}
              />
            </label>
          </div>

          <label>
            Error logs
            <textarea
              className="log-box"
              onChange={(event) => setDraft({ ...draft, error_logs: event.target.value })}
              placeholder="Paste sanitized logs or response body"
              value={draft.error_logs}
            />
          </label>

          <div className="sample-row">
            {samples.map((sample) => (
              <button key={sample.title} onClick={() => setDraft(sample)} type="button">
                {sample.product_area}
              </button>
            ))}
          </div>

          <button className="primary-button" disabled={!canAnalyze} onClick={handleAnalyze} type="button">
            {busy === "analyze" ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
            Analyze case
          </button>
        </aside>

        <section className="panel output-panel">
          <div className="panel-title">
            <div>
              <span>Support response</span>
              <strong>{currentOutput ? currentOutput.category : "Waiting for analysis"}</strong>
            </div>
            <MessageSquareText size={20} />
          </div>

          {busy === "boot" || busy === "analyze" ? <SkeletonOutput /> : null}

          {!currentOutput && busy !== "boot" && busy !== "analyze" ? (
            <div className="empty-state">
              <Sparkles size={32} />
              <p>Select a sample or paste a case, then run analysis.</p>
            </div>
          ) : null}

          {currentOutput ? (
            <div className="analysis-stack">
              <div className="meta-row">
                <span className={priorityClass}>{currentOutput.priority}</span>
                <span className="meta-chip">{currentOutput.provider}</span>
                <span className="meta-chip">{result?.retrieved_docs.length ?? 0} docs</span>
              </div>

              <section className="answer-block">
                <div className="block-head">
                  <h2>Summary</h2>
                </div>
                <p>{currentOutput.summary}</p>
              </section>

              <section className="answer-block">
                <div className="block-head">
                  <h2>Customer reply</h2>
                  <button onClick={() => copyText("reply", currentOutput.customer_reply)} type="button">
                    {copied === "reply" ? <Check size={15} /> : <Clipboard size={15} />}
                    Copy
                  </button>
                </div>
                <p className="reply-text">{currentOutput.customer_reply}</p>
              </section>

              <section className="answer-block">
                <div className="block-head">
                  <h2>Troubleshooting</h2>
                </div>
                <ol className="steps-list">
                  {currentOutput.troubleshooting_steps.map((step, index) => (
                    <li key={`${step.label}-${index}`}>
                      <span>{index + 1}</span>
                      <div>
                        <strong>{step.label}</strong>
                        <p>{step.detail}</p>
                      </div>
                    </li>
                  ))}
                </ol>
              </section>
            </div>
          ) : null}
        </section>

        <aside className="panel kb-panel">
          <div className="panel-title">
            <div>
              <span>Knowledge base</span>
              <strong>{currentOutput ? "Generated article" : "KB draft"}</strong>
            </div>
            <BookOpen size={20} />
          </div>

          {currentOutput ? (
            <>
              <div className="tag-row">
                {currentOutput.tags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
              <pre className="markdown-preview">{currentOutput.kb_article}</pre>
              <div className="kb-actions">
                <button className="secondary-button" onClick={() => copyText("kb", currentOutput.kb_article)} type="button">
                  {copied === "kb" ? <Check size={16} /> : <Clipboard size={16} />}
                  Copy Markdown
                </button>
                <button className="secondary-button solid" disabled={busy === "save"} onClick={handleSaveKb} type="button">
                  {busy === "save" ? <Loader2 className="spin" size={16} /> : <Save size={16} />}
                  Save KB
                </button>
                <button className="secondary-button" disabled={busy === "latex"} onClick={handleGenerateLatex} type="button">
                  {busy === "latex" ? <Loader2 className="spin" size={16} /> : <FileDown size={16} />}
                  Export LaTeX
                </button>
              </div>
              {latexReport ? <p className="export-note">Saved {latexReport.filename}</p> : null}
              <div className="internal-notes">
                <strong>Internal notes</strong>
                <p>{currentOutput.internal_notes}</p>
              </div>
            </>
          ) : (
            <div className="empty-state compact-empty">
              <BookOpen size={30} />
              <p>Analyze a case to preview a knowledge base draft here.</p>
            </div>
          )}
        </aside>
      </section>
    </main>
  );
}

function SkeletonOutput() {
  return (
    <div className="skeleton-stack" aria-hidden="true">
      <div />
      <div />
      <div />
      <div />
    </div>
  );
}

function errorMessage(value: unknown) {
  return value instanceof Error ? value.message : "Unexpected error.";
}

function downloadTexFile(report: LatexReportResponse) {
  const blob = new Blob([report.tex], { type: "application/x-tex;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = report.filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
