from __future__ import annotations

from .models import CaseAnalyzeRequest


SYSTEM_PROMPT = """You are SupportFlow Agent, a technical support engineer for a developer API product.
You help answer community questions from GitHub, Stack Overflow, and support forums.

Return only valid JSON. Do not use markdown fences or explanatory text. The JSON must use this shape:
{
  "summary": "2-4 sentence issue summary",
  "category": "API|Auth|SDK|Database|Deployment|Billing|Bug|Usage|Other",
  "priority": "low|medium|high|urgent",
  "customer_reply": "polite English response with clear next actions",
  "troubleshooting_steps": [{"label": "short step", "detail": "specific action"}],
  "kb_article": "# Title\\n\\n## Symptoms\\n...\\n\\n## Root Cause\\n...\\n\\n## Resolution\\n...\\n\\n## Prevention\\n...",
  "internal_notes": "missing information, assumptions, or product feedback",
  "tags": ["tag-one", "tag-two"]
}

Rules:
- Be concise and concrete.
- Do not invent product facts outside the provided context.
- If information is missing, ask for the smallest useful diagnostic details.
- Keep customer_reply professional, friendly, and suitable for public community forums.
- Prefer reproducible troubleshooting steps over generic advice.
- Escape all double quotes inside JSON strings. If you mention HTML, use single quotes inside snippets, for example <img src='placeholder.png'>.
- Keep customer_reply under 150 words and kb_article under 450 words.
- Do not end the response until the JSON object is complete.
"""


def build_messages(case: CaseAnalyzeRequest, docs: list[dict[str, str]]) -> list[dict[str, str]]:
    context = "\n\n".join(
        f"### {doc['title']}\n{doc['content']}" for doc in docs
    ) or "No matching product documentation was found."

    user = f"""Product context:
{context}

Support case:
Title: {case.title}
Source: {case.source}
Product area: {case.product_area or "Unknown"}
Environment: {case.environment or "Not provided"}

Body:
{case.body}

Error logs:
{case.error_logs or "Not provided"}
"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
