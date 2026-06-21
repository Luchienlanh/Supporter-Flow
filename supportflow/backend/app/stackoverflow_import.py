from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass

import requests


QUESTION_PATTERNS = (
    re.compile(r"^https?://stackoverflow\.com/questions/(\d+)(?:/[^?#]*)?(?:[?#].*)?$"),
    re.compile(r"^https?://stackoverflow\.com/q/(\d+)(?:[/?#].*)?$"),
)
TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class StackOverflowRef:
    question_id: int


def parse_question_url(url: str) -> StackOverflowRef:
    value = url.strip()
    for pattern in QUESTION_PATTERNS:
        match = pattern.match(value)
        if match:
            return StackOverflowRef(question_id=int(match.group(1)))
    raise ValueError("Enter a Stack Overflow question URL like https://stackoverflow.com/questions/123/title.")


def fetch_question(url: str) -> dict[str, object]:
    ref = parse_question_url(url)
    question = _get_items(
        f"https://api.stackexchange.com/2.3/questions/{ref.question_id}",
        {
            "site": "stackoverflow",
            "filter": "withbody",
        },
    )
    if not question:
        raise ValueError("Stack Overflow question was not found or is not public.")

    answers = _get_items(
        f"https://api.stackexchange.com/2.3/questions/{ref.question_id}/answers",
        {
            "site": "stackoverflow",
            "filter": "withbody",
            "sort": "votes",
            "order": "desc",
            "pagesize": 3,
        },
    )
    comments = _get_items(
        f"https://api.stackexchange.com/2.3/questions/{ref.question_id}/comments",
        {
            "site": "stackoverflow",
            "filter": "withbody",
            "sort": "creation",
            "order": "asc",
            "pagesize": 5,
        },
    )

    item = question[0]
    tags = item.get("tags") or []
    body_parts = [
        f"Stack Overflow question: {item.get('link') or url}",
        f"Question ID: {ref.question_id}",
        f"Score: {item.get('score', 0)}",
        f"Tags: {', '.join(tags) if tags else 'none'}",
        f"Accepted answer ID: {item.get('accepted_answer_id', 'none')}",
        "",
        "Question body:",
        _clean_html(str(item.get("body") or "")),
    ]

    if comments:
        body_parts.append("\nQuestion comments:")
        for index, comment in enumerate(comments, start=1):
            owner = comment.get("owner", {}).get("display_name", "unknown")
            body_parts.append(f"\nComment {index} by {owner}:\n{_clean_html(str(comment.get('body') or ''))}")

    if answers:
        body_parts.append("\nTop answers:")
        for index, answer in enumerate(answers, start=1):
            owner = answer.get("owner", {}).get("display_name", "unknown")
            accepted = "accepted" if answer.get("is_accepted") else "not accepted"
            body_parts.append(
                f"\nAnswer {index} by {owner} ({accepted}, score {answer.get('score', 0)}):\n"
                f"{_clean_html(str(answer.get('body') or ''))}"
            )

    return {
        "title": html.unescape(str(item.get("title") or f"Stack Overflow question {ref.question_id}")),
        "body": "\n".join(body_parts).strip(),
        "environment": ", ".join(tags[:4]) if tags else "",
        "product_area": "Stack Overflow Q&A",
        "question_url": item.get("link") or url,
        "question_id": ref.question_id,
        "tags": tags,
    }


def _get_items(url: str, params: dict[str, object]) -> list[dict[str, object]]:
    api_key = os.environ.get("STACK_EXCHANGE_KEY", "")
    if api_key:
        params = {**params, "key": api_key}
    response = requests.get(url, params=params, timeout=30)
    if response.status_code == 400:
        raise ValueError(f"Stack Exchange rejected the request: {response.text[:300]}")
    if response.status_code in {402, 403}:
        raise RuntimeError("Stack Exchange API quota or permission error. Try again later or set STACK_EXCHANGE_KEY.")
    response.raise_for_status()
    payload = response.json()
    return payload.get("items") or []


def _clean_html(value: str) -> str:
    text = re.sub(r"</(?:p|li|pre|blockquote|h[1-6])>", "\n", value)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = TAG_RE.sub("", text)
    text = html.unescape(text)
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line.strip()).strip()

