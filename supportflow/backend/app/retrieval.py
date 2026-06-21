from __future__ import annotations

import re

from .db import connect


def search_documents(query: str, limit: int = 4) -> list[dict[str, str]]:
    terms = _terms(query)
    if not terms:
        return []
    fts_query = " OR ".join(terms[:12])
    with connect() as conn:
        try:
            rows = conn.execute(
                """
                SELECT d.title, d.content
                FROM documents_fts f
                JOIN documents d ON d.id = f.rowid
                WHERE documents_fts MATCH ?
                ORDER BY bm25(documents_fts)
                LIMIT ?
                """,
                (fts_query, limit),
            ).fetchall()
        except Exception:
            like = f"%{terms[0]}%"
            rows = conn.execute(
                """
                SELECT title, content
                FROM documents
                WHERE title LIKE ? OR content LIKE ?
                LIMIT ?
                """,
                (like, like, limit),
            ).fetchall()
    return [{"title": row["title"], "content": _trim(row["content"])} for row in rows]


def _terms(query: str) -> list[str]:
    return [
        term.lower()
        for term in re.findall(r"[A-Za-z0-9_]{3,}", query)
        if term.lower() not in {"the", "and", "for", "with", "this", "that", "from"}
    ]


def _trim(text: str, max_chars: int = 1400) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit("\n", 1)[0] + "\n..."

