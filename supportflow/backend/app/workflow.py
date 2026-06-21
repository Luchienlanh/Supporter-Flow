from __future__ import annotations

import json
from typing import Any, TypedDict

from langchain_core.runnables import RunnableLambda, RunnableSequence

from .models import CaseAnalyzeRequest
from .providers import LLMClient
from .retrieval import search_documents


class WorkflowState(TypedDict, total=False):
    case: CaseAnalyzeRequest
    client: LLMClient
    docs: list[dict[str, str]]
    classification: dict[str, Any]
    troubleshooting: dict[str, Any]
    reply: dict[str, Any]
    kb: dict[str, Any]
    validation: dict[str, Any]
    raw: dict[str, Any]
    provider: str
    model: str


def build_support_workflow() -> RunnableSequence:
    return (
        RunnableLambda(retrieve_docs)
        | RunnableLambda(classify_case)
        | RunnableLambda(plan_troubleshooting)
        | RunnableLambda(write_customer_reply)
        | RunnableLambda(write_kb_article)
        | RunnableLambda(validate_and_merge)
    )


def retrieve_docs(state: WorkflowState) -> WorkflowState:
    case = state["case"]
    query = " ".join([case.title, case.body, case.error_logs, case.product_area])
    return {**state, "docs": search_documents(query)}


def classify_case(state: WorkflowState) -> WorkflowState:
    case = state["case"]
    docs = state.get("docs", [])
    raw = _call_json(
        state["client"],
        "You are a technical support classifier. Return only JSON.",
        f"""Classify this support case.

Allowed categories: API, Auth, SDK, Database, Deployment, Billing, Bug, Usage, Other.
Allowed priorities: low, medium, high, urgent.

Return JSON:
{{
  "summary": "2-3 sentence summary",
  "category": "one allowed category",
  "priority": "one allowed priority",
  "missing_info": ["smallest useful missing diagnostic detail"],
  "tags": ["3-6 short tags"],
  "product_feedback": "short internal product feedback"
}}

Case:
Title: {case.title}
Source: {case.source}
Product area: {case.product_area or "Unknown"}
Environment: {case.environment or "Not provided"}

Body:
{_clip(case.body, 6000)}

Error logs:
{_clip(case.error_logs or "Not provided", 2000)}

Relevant docs:
{_format_docs(docs)}
""",
    )
    return {**state, "classification": raw}


def plan_troubleshooting(state: WorkflowState) -> WorkflowState:
    case = state["case"]
    classification = state.get("classification", {})
    raw = _call_json(
        state["client"],
        "You are a technical support engineer. Return only JSON.",
        f"""Create reproducible troubleshooting steps for the support case.

Return JSON:
{{
  "steps": [
    {{"label": "short action", "detail": "specific instruction"}}
  ],
  "escalation": "when to escalate to senior engineer"
}}

Classification:
{json.dumps(classification, ensure_ascii=False)}

Case body:
{_clip(case.body, 5000)}

Docs:
{_format_docs(state.get("docs", []))}
""",
    )
    return {**state, "troubleshooting": raw}


def write_customer_reply(state: WorkflowState) -> WorkflowState:
    case = state["case"]
    raw = _call_json(
        state["client"],
        "You write concise customer-facing technical support replies. Return only JSON.",
        f"""Draft an English community-support reply.

Rules:
- Under 180 words.
- Be polite and concrete.
- If the issue is already solved in answers/comments, acknowledge the likely resolution.
- Do not overclaim root cause if evidence is weak.
- Escape quotes inside JSON strings.

Return JSON:
{{"customer_reply": "reply text"}}

Classification:
{json.dumps(state.get("classification", {}), ensure_ascii=False)}

Troubleshooting:
{json.dumps(state.get("troubleshooting", {}), ensure_ascii=False)}

Case:
{_clip(case.body, 5000)}
""",
    )
    return {**state, "reply": raw}


def write_kb_article(state: WorkflowState) -> WorkflowState:
    raw = _call_json(
        state["client"],
        "You write internal knowledge base articles. Return only JSON.",
        f"""Create a reusable Markdown KB article from the support case.

Rules:
- Under 450 words.
- Use Markdown headings.
- Keep it grounded in the case and retrieved docs.
- Escape newlines as \\n inside the JSON string.

Return JSON:
{{"kb_article": "# Title\\n\\n## Symptoms\\n...\\n\\n## Root Cause\\n...\\n\\n## Resolution\\n...\\n\\n## Prevention\\n..."}}

Classification:
{json.dumps(state.get("classification", {}), ensure_ascii=False)}

Troubleshooting:
{json.dumps(state.get("troubleshooting", {}), ensure_ascii=False)}

Customer reply:
{json.dumps(state.get("reply", {}), ensure_ascii=False)}

Docs:
{_format_docs(state.get("docs", []))}
""",
    )
    return {**state, "kb": raw}


def validate_and_merge(state: WorkflowState) -> WorkflowState:
    client = state["client"]
    classification = state.get("classification", {})
    troubleshooting = state.get("troubleshooting", {})
    reply = state.get("reply", {})
    kb = state.get("kb", {})
    validation = _call_json(
        client,
        "You validate support outputs. Return only JSON.",
        f"""Validate the support output for safety and completeness.

Return JSON:
{{"is_usable": true, "notes": "short validation notes"}}

Classification:
{json.dumps(classification, ensure_ascii=False)}

Troubleshooting:
{json.dumps(troubleshooting, ensure_ascii=False)}

Reply:
{json.dumps(reply, ensure_ascii=False)}

KB:
{json.dumps(kb, ensure_ascii=False)}
""",
    )

    raw = {
        "summary": classification.get("summary") or "Support case analyzed.",
        "category": classification.get("category") or "Other",
        "priority": classification.get("priority") or "medium",
        "customer_reply": reply.get("customer_reply") or "Thanks for the report. We are checking the issue and will follow up with next steps.",
        "troubleshooting_steps": troubleshooting.get("steps") or [],
        "kb_article": kb.get("kb_article") or "# Support Case\n\n## Resolution\nAdd the verified resolution here.",
        "internal_notes": _internal_notes(classification, troubleshooting, validation),
        "tags": classification.get("tags") or [],
        "workflow": {
            "engine": "langchain",
            "steps": [
                "retrieve_docs",
                "classify_case",
                "plan_troubleshooting",
                "write_customer_reply",
                "write_kb_article",
                "validate_and_merge",
            ],
        },
    }
    return {
        **state,
        "validation": validation,
        "raw": raw,
        "provider": getattr(client, "provider", ""),
        "model": getattr(client, "model", ""),
    }


def _call_json(client: LLMClient, system: str, user: str) -> dict[str, Any]:
    result = client.chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
    )
    from .services import fallback_raw_output, parse_json_object

    try:
        return parse_json_object(result.content)
    except ValueError as exc:
        return fallback_raw_output(result.content, str(exc))


def _format_docs(docs: list[dict[str, str]]) -> str:
    if not docs:
        return "No matching product documentation was found."
    return "\n\n".join(f"### {doc['title']}\n{_clip(doc['content'], 1400)}" for doc in docs)


def _clip(value: str, limit: int) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit("\n", 1)[0] + "\n..."


def _internal_notes(classification: dict[str, Any], troubleshooting: dict[str, Any], validation: dict[str, Any]) -> str:
    parts = []
    if classification.get("missing_info"):
        parts.append("Missing info: " + "; ".join(str(item) for item in classification["missing_info"]))
    if classification.get("product_feedback"):
        parts.append("Product feedback: " + str(classification["product_feedback"]))
    if troubleshooting.get("escalation"):
        parts.append("Escalation: " + str(troubleshooting["escalation"]))
    if validation.get("notes"):
        parts.append("Validation: " + str(validation["notes"]))
    return "\n".join(parts) if parts else "LangChain workflow completed without additional notes."

