from __future__ import annotations

import json
import re
from typing import Any

from . import db
from .models import AgentOutput, CaseAnalyzeRequest, TroubleshootingStep
from .providers import ProviderConfigError, get_client
from .workflow import build_support_workflow


ALLOWED_CATEGORIES = {"API", "Auth", "SDK", "Database", "Deployment", "Billing", "Bug", "Usage", "Other"}
ALLOWED_PRIORITIES = {"low", "medium", "high", "urgent"}


def analyze_case(request: CaseAnalyzeRequest) -> tuple[int, AgentOutput, list[str]]:
    case_id = db.create_case(request.model_dump())
    client = get_client(request.provider)
    try:
        state = build_support_workflow().invoke({"case": request, "client": client})
        raw = state["raw"]
        output = normalize_output(raw, state["provider"], state["model"])
        db.save_case_output(case_id, output, raw)
    except Exception:
        db.mark_case_failed(case_id)
        raise
    return case_id, output, [doc["title"] for doc in state.get("docs", [])]


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    try:
        parsed = json.loads(stripped, strict=False)
    except json.JSONDecodeError:
        candidate = _extract_json_object(stripped)
        if not candidate:
            raise ValueError("The LLM response did not include a JSON object.")
        parsed = json.loads(candidate, strict=False)
    if not isinstance(parsed, dict):
        raise ValueError("The LLM response JSON must be an object.")
    return parsed


def fallback_raw_output(content: str, reason: str) -> dict[str, Any]:
    trimmed = content.strip()
    if trimmed.startswith("```"):
        trimmed = re.sub(r"^```(?:json)?", "", trimmed, flags=re.IGNORECASE).strip()
        trimmed = re.sub(r"```$", "", trimmed).strip()

    summary = _extract_text_field(trimmed, "summary") or "SupportFlow recovered a malformed model response and preserved the usable draft content."
    category = _extract_enum_field(trimmed, "category", ALLOWED_CATEGORIES) or "Other"
    priority = _extract_enum_field(trimmed, "priority", ALLOWED_PRIORITIES) or "medium"
    customer_reply = _extract_text_field(trimmed, "customer_reply") or trimmed[:1800] or "The model returned an empty response."
    kb_article = _extract_text_field(trimmed, "kb_article")
    if not kb_article:
        kb_article = (
            "# Draft Knowledge Base Article\n\n"
            "## Symptoms\nThe imported issue needs manual review.\n\n"
            "## Root Cause\nThe model response was malformed before a complete article could be parsed.\n\n"
            "## Resolution\nReview the recovered reply and troubleshooting steps, then save a verified article.\n\n"
            "## Prevention\nRetry with a shorter issue body or switch provider."
        )
    steps = _extract_steps(trimmed)
    if not steps:
        steps = [
            {
                "label": "Review the recovered draft",
                "detail": "The LLM response was malformed, but SupportFlow recovered the usable text fields.",
            }
        ]
    tags = _extract_tags(trimmed) or ["auto-repaired", "manual-review"]

    return {
        "summary": summary,
        "category": category,
        "priority": priority,
        "customer_reply": customer_reply,
        "troubleshooting_steps": steps,
        "kb_article": kb_article,
        "internal_notes": f"Auto-repaired malformed LLM JSON. Parser reason: {reason}",
        "tags": tags,
    }


def _extract_text_field(text: str, key: str) -> str:
    keys = (
        "summary",
        "category",
        "priority",
        "customer_reply",
        "troubleshooting_steps",
        "kb_article",
        "internal_notes",
        "tags",
    )
    match = re.search(rf'"{re.escape(key)}"\s*:\s*"', text)
    if not match:
        return ""
    start = match.end()
    next_key = re.search(
        r',?\s*\n\s*"(?:' + "|".join(re.escape(item) for item in keys if item != key) + r')"\s*:',
        text[start:],
    )
    end = start + next_key.start() if next_key else len(text)
    value = text[start:end].strip()
    value = re.sub(r'"\s*,?\s*$', "", value, flags=re.DOTALL)
    return _decode_jsonish(value)


def _extract_enum_field(text: str, key: str, allowed: set[str]) -> str:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*"([^"\n\r]+)"', text)
    if not match:
        return ""
    value = match.group(1).strip()
    if value in allowed:
        return value
    lower_map = {item.lower(): item for item in allowed}
    return lower_map.get(value.lower(), "")


def _extract_steps(text: str) -> list[dict[str, str]]:
    steps: list[dict[str, str]] = []
    pattern = re.compile(
        r'\{\s*"label"\s*:\s*"(?P<label>.*?)"\s*,\s*"detail"\s*:\s*"(?P<detail>.*?)"\s*\}',
        flags=re.DOTALL,
    )
    for match in pattern.finditer(text):
        label = _decode_jsonish(match.group("label"))
        detail = _decode_jsonish(match.group("detail"))
        if label:
            steps.append({"label": label, "detail": detail})
        if len(steps) >= 6:
            break
    return steps


def _extract_tags(text: str) -> list[str]:
    match = re.search(r'"tags"\s*:\s*\[(.*?)\]', text, flags=re.DOTALL)
    if not match:
        return []
    tags = re.findall(r'"([^"\n\r]+)"', match.group(1))
    return [tag.strip().lower().replace(" ", "-") for tag in tags if tag.strip()][:6]


def _decode_jsonish(value: str) -> str:
    cleaned = value.strip()
    try:
        return json.loads(f'"{cleaned}"', strict=False)
    except json.JSONDecodeError:
        return (
            cleaned.replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace('\\"', '"')
            .replace("\\/", "/")
            .strip()
        )


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    if start < 0:
        return ""

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return text[start:]


def normalize_output(raw: dict[str, Any], provider: str, model: str) -> AgentOutput:
    category = str(raw.get("category") or "Other").strip()
    if category not in ALLOWED_CATEGORIES:
        category = "Other"
    priority = str(raw.get("priority") or "medium").strip().lower()
    if priority not in ALLOWED_PRIORITIES:
        priority = "medium"

    steps_raw = raw.get("troubleshooting_steps") or []
    steps: list[TroubleshootingStep] = []
    if isinstance(steps_raw, list):
        for item in steps_raw:
            if isinstance(item, dict):
                label = str(item.get("label") or item.get("step") or "").strip()
                detail = str(item.get("detail") or "").strip()
            else:
                label = str(item).strip()
                detail = ""
            if label:
                steps.append(TroubleshootingStep(label=label, detail=detail))
    if not steps:
        steps = [TroubleshootingStep(label="Collect diagnostics", detail="Ask for logs, request ID, timestamp, and reproduction steps.")]

    tags = raw.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    clean_tags = [str(tag).strip().lower().replace(" ", "-") for tag in tags if str(tag).strip()][:6]

    kb_article = raw.get("kb_article") or ""
    if isinstance(kb_article, dict):
        kb_article = _kb_dict_to_markdown(kb_article)
    kb_article = str(kb_article).strip() or "# Support Case\n\n## Resolution\nAdd the verified resolution here."

    return AgentOutput(
        summary=str(raw.get("summary") or "Support case analyzed.").strip(),
        category=category,
        priority=priority,  # type: ignore[arg-type]
        customer_reply=str(raw.get("customer_reply") or "Thanks for the report. We are checking the issue and will follow up with next steps.").strip(),
        troubleshooting_steps=steps,
        kb_article=kb_article,
        internal_notes=str(raw.get("internal_notes") or "No internal notes.").strip(),
        tags=clean_tags,
        provider=provider,
        model=model,
    )


def _kb_dict_to_markdown(value: dict[str, Any]) -> str:
    title = str(value.get("title") or "Knowledge Base Article")
    parts = [f"# {title}"]
    for key in ("symptoms", "root_cause", "resolution", "prevention"):
        if key in value:
            heading = key.replace("_", " ").title()
            parts.append(f"\n## {heading}\n{value[key]}")
    return "\n".join(parts)
