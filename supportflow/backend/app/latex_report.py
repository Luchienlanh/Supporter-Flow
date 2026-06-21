from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict

from langchain_core.runnables import RunnableLambda, RunnableSequence

from . import db
from .models import CaseRecord, LatexReportRequest, LatexReportResponse, TroubleshootingStep
from .providers import LLMClient, get_client


APP_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = APP_ROOT / "backend" / "templates" / "company_issue_report.tex"
EXPORT_DIR = APP_ROOT / "exports"


class LatexReportState(TypedDict, total=False):
    case: CaseRecord
    options: LatexReportRequest
    client: LLMClient
    raw_fields: dict[str, Any]
    fields: dict[str, Any]
    tex: str
    filename: str
    path: Path


def generate_latex_report(case: CaseRecord, options: LatexReportRequest) -> LatexReportResponse:
    client = get_client(options.provider)
    state = build_latex_report_workflow().invoke({"case": case, "options": options, "client": client})
    path = state["path"]
    return LatexReportResponse(
        case_id=case.id,
        filename=state["filename"],
        path=str(path),
        tex=state["tex"],
    )


def build_latex_report_workflow() -> RunnableSequence:
    return (
        RunnableLambda(draft_report_fields)
        | RunnableLambda(normalize_report_fields)
        | RunnableLambda(render_latex_report)
        | RunnableLambda(save_latex_report)
    )


def draft_report_fields(state: LatexReportState) -> LatexReportState:
    case = state["case"]
    output = case.output
    if output is None:
        raise ValueError("A LaTeX report can only be generated from an analyzed case.")

    raw = _call_report_json(
        state["client"],
        "You are a technical support documentation agent. Return only strict JSON.",
        f"""Convert this analyzed support case into a concise company-style issue report.

Rules:
- Use only facts available in the issue and analyzed support output.
- Write in professional English.
- Do not include Markdown or LaTeX.
- Keep summaries short enough for a one to two page support document.
- Return only JSON with double-quoted strings.

Return JSON:
{{
  "document_title": "Technical Support Issue Report",
  "question_summary": "What the requester asked and the visible symptom.",
  "answer_summary": "The support answer or recommended resolution.",
  "resolution_status": "Resolved | Workaround Provided | Pending Customer Input | Escalation Recommended",
  "follow_up_actions": ["specific follow-up action"],
  "kb_summary": "Reusable lesson learned for the knowledge base.",
  "internal_notes": "Risk, missing information, or product feedback."
}}

Case:
Title: {case.title}
Source: {case.source}
Product area: {case.product_area or "Unknown"}
Environment: {case.environment or "Not provided"}

Issue body:
{_clip(case.body, 5000)}

Error logs:
{_clip(case.error_logs or "Not provided", 1600)}

Analyzed output:
{json.dumps(output.model_dump(), ensure_ascii=False)}
""",
    )
    return {**state, "raw_fields": raw}


def normalize_report_fields(state: LatexReportState) -> LatexReportState:
    case = state["case"]
    defaults = _default_fields(case)
    raw = state.get("raw_fields", {})

    fields = {
        "document_title": _clean_text(raw.get("document_title")) or defaults["document_title"],
        "question_summary": _clean_text(raw.get("question_summary")) or defaults["question_summary"],
        "answer_summary": _clean_text(raw.get("answer_summary")) or defaults["answer_summary"],
        "resolution_status": _clean_text(raw.get("resolution_status")) or defaults["resolution_status"],
        "follow_up_actions": _clean_list(raw.get("follow_up_actions")) or defaults["follow_up_actions"],
        "kb_summary": _clean_text(raw.get("kb_summary")) or defaults["kb_summary"],
        "internal_notes": _clean_text(raw.get("internal_notes")) or defaults["internal_notes"],
    }
    return {**state, "fields": fields}


def render_latex_report(state: LatexReportState) -> LatexReportState:
    case = state["case"]
    options = state["options"]
    fields = state["fields"]
    output = case.output
    if output is None:
        raise ValueError("A LaTeX report can only be generated from an analyzed case.")

    today = datetime.now()
    report_id = f"SF-CASE-{case.id:04d}-{today:%Y%m%d}"
    replacements = {
        "company_name": _tex_text(options.company_name),
        "document_title": _tex_text(fields["document_title"]),
        "report_id": _tex_text(report_id),
        "prepared_for": _tex_text(options.prepared_for),
        "prepared_by": _tex_text(options.prepared_by),
        "prepared_date": _tex_text(today.strftime("%Y-%m-%d %H:%M")),
        "case_id": _tex_text(str(case.id)),
        "issue_source": _tex_text(_source_label(case.source)),
        "issue_title": _tex_text(case.title),
        "product_area": _tex_text(case.product_area or "Not provided"),
        "environment": _tex_text(case.environment or "Not provided"),
        "case_status": _tex_text(case.status.title()),
        "category": _tex_text(output.category),
        "priority": _tex_text(output.priority.upper()),
        "analysis_model": _tex_text(f"{output.provider} / {output.model}"),
        "question_summary": _tex_block(fields["question_summary"]),
        "answer_summary": _tex_block(fields["answer_summary"]),
        "troubleshooting_items": _tex_steps(output.troubleshooting_steps),
        "resolution_status": _tex_text(fields["resolution_status"]),
        "follow_up_items": _tex_items(fields["follow_up_actions"]),
        "kb_summary": _tex_block(fields["kb_summary"]),
        "internal_notes": _tex_block(fields["internal_notes"]),
    }

    tex = _load_template()
    for key, value in replacements.items():
        tex = tex.replace("{{" + key + "}}", value)
    return {**state, "tex": tex}


def save_latex_report(state: LatexReportState) -> LatexReportState:
    case = state["case"]
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"issue_report_case_{case.id}_{datetime.now():%Y%m%d_%H%M%S}.tex"
    path = EXPORT_DIR / filename
    path.write_text(state["tex"], encoding="utf-8")
    return {**state, "filename": filename, "path": path}


def _call_report_json(client: LLMClient, system: str, user: str) -> dict[str, Any]:
    result = client.chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
    )
    try:
        from .services import parse_json_object

        return parse_json_object(result.content)
    except Exception as exc:
        return {
            "internal_notes": (
                "Report agent received malformed JSON and used deterministic fields. "
                f"Parser reason: {exc}"
            )
        }


def _default_fields(case: CaseRecord) -> dict[str, Any]:
    output = case.output
    if output is None:
        raise ValueError("A LaTeX report can only be generated from an analyzed case.")

    return {
        "document_title": "Technical Support Issue Report",
        "question_summary": output.summary,
        "answer_summary": output.customer_reply,
        "resolution_status": "Pending customer confirmation",
        "follow_up_actions": ["Confirm the requester can reproduce the resolution.", "Save verified findings to the knowledge base."],
        "kb_summary": _plain_markdown(output.kb_article),
        "internal_notes": output.internal_notes,
    }


def _load_template() -> str:
    if TEMPLATE_PATH.exists():
        return TEMPLATE_PATH.read_text(encoding="utf-8")
    raise FileNotFoundError(f"LaTeX template not found: {TEMPLATE_PATH}")


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return ""
    return str(value).strip()


def _clean_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()][:6]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _plain_markdown(markdown: str) -> str:
    text = re.sub(r"^#{1,6}\s*", "", markdown, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return _clip(text, 900)


def _source_label(source: str) -> str:
    labels = {
        "github": "GitHub Issue",
        "stackoverflow": "Stack Overflow Question",
        "paste": "Manual Intake",
        "sample": "Sample Case",
    }
    return labels.get(source, source.title())


def _tex_text(value: str) -> str:
    return _latex_escape(value.strip() or "N/A")


def _tex_block(value: str) -> str:
    text = value.strip()
    if not text:
        return "N/A"
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        paragraphs = [text]
    return "\n\n".join(_latex_escape(part.replace("\n", " ")) for part in paragraphs)


def _tex_items(items: list[str]) -> str:
    if not items:
        return r"\item N/A"
    return "\n".join(rf"\item {_latex_escape(item)}" for item in items)


def _tex_steps(steps: list[TroubleshootingStep]) -> str:
    if not steps:
        return r"\item N/A"
    lines = []
    for step in steps:
        label = _latex_escape(step.label)
        detail = _latex_escape(step.detail)
        if detail:
            lines.append(rf"\item \textbf{{{label}.}} {detail}")
        else:
            lines.append(rf"\item {label}")
    return "\n".join(lines)


def _latex_escape(value: str) -> str:
    value = _normalize_for_latex(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    breakable = {"/", ":", "-"}
    parts = []
    for char in value:
        escaped = replacements.get(char, char)
        if char in breakable:
            escaped += r"\allowbreak{}"
        parts.append(escaped)
    return "".join(parts)


def _normalize_for_latex(value: str) -> str:
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
        "\u00a0": " ",
        "\u200b": "",
        "\ufeff": "",
        "\u2192": "->",
        "\u2265": ">=",
        "\u2264": "<=",
        "\u00d7": "x",
    }
    return "".join(replacements.get(char, char) for char in value)


def _clip(value: str, limit: int) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit("\n", 1)[0] + "\n..."
