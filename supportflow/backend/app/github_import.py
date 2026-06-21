from __future__ import annotations

import os
import re
from dataclasses import dataclass

import requests


ISSUE_RE = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/issues/(\d+)(?:[/?#].*)?$")


@dataclass(frozen=True)
class IssueRef:
    owner: str
    repo: str
    number: int


def parse_issue_url(url: str) -> IssueRef:
    match = ISSUE_RE.match(url.strip())
    if not match:
        raise ValueError("Enter a GitHub issue URL like https://github.com/owner/repo/issues/123.")
    owner, repo, number = match.groups()
    return IssueRef(owner=owner, repo=repo, number=int(number))


def fetch_issue(url: str) -> dict[str, object]:
    ref = parse_issue_url(url)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "supportflow-agent",
    }
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    api_url = f"https://api.github.com/repos/{ref.owner}/{ref.repo}/issues/{ref.number}"
    response = requests.get(api_url, headers=headers, timeout=30)
    if response.status_code == 403:
        raise RuntimeError("GitHub rate limit or permission error. Add GITHUB_TOKEN for higher limits/private repos.")
    response.raise_for_status()
    issue = response.json()

    comments = []
    comments_url = issue.get("comments_url")
    if comments_url and issue.get("comments", 0):
        comments_response = requests.get(comments_url, headers=headers, timeout=30)
        comments_response.raise_for_status()
        comments = comments_response.json()[:5]

    label_names = [label.get("name", "") for label in issue.get("labels", [])]
    body_parts = [
        f"Repository: {ref.owner}/{ref.repo}",
        f"Issue: #{ref.number}",
        f"Labels: {', '.join(label_names) if label_names else 'none'}",
        "",
        issue.get("body") or "",
    ]
    if comments:
        body_parts.append("\nRecent comments:")
        for index, comment in enumerate(comments, start=1):
            author = comment.get("user", {}).get("login", "unknown")
            body_parts.append(f"\nComment {index} by {author}:\n{comment.get('body') or ''}")

    return {
        "title": issue.get("title") or f"Issue #{ref.number}",
        "body": "\n".join(body_parts).strip(),
        "issue_url": issue.get("html_url") or url,
        "repository": f"{ref.owner}/{ref.repo}",
        "issue_number": ref.number,
    }

