from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .models import AgentOutput, CaseListItem, CaseRecord, KbArticle, TroubleshootingStep


APP_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = APP_ROOT / "supportflow.db"
SEED_DOCS_DIR = APP_ROOT.parent / "data" / "seed_docs"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db_path() -> Path:
    configured = Path(os.environ.get("SUPPORTFLOW_DB_PATH", str(DEFAULT_DB_PATH))).expanduser()
    if configured.is_absolute():
        return configured
    return APP_ROOT / configured


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cases (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source TEXT NOT NULL,
              title TEXT NOT NULL,
              body TEXT NOT NULL,
              error_logs TEXT NOT NULL DEFAULT '',
              environment TEXT NOT NULL DEFAULT '',
              product_area TEXT NOT NULL DEFAULT '',
              status TEXT NOT NULL DEFAULT 'new',
              category TEXT,
              priority TEXT,
              tags_json TEXT NOT NULL DEFAULT '[]',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS case_outputs (
              case_id INTEGER PRIMARY KEY,
              provider TEXT NOT NULL,
              model TEXT NOT NULL,
              summary TEXT NOT NULL,
              customer_reply TEXT NOT NULL,
              troubleshooting_json TEXT NOT NULL,
              kb_markdown TEXT NOT NULL,
              internal_notes TEXT NOT NULL,
              raw_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS kb_articles (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,
              category TEXT NOT NULL,
              markdown TEXT NOT NULL,
              source_case_id INTEGER,
              created_at TEXT NOT NULL,
              FOREIGN KEY(source_case_id) REFERENCES cases(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS documents (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              slug TEXT NOT NULL UNIQUE,
              title TEXT NOT NULL,
              content TEXT NOT NULL,
              tags_json TEXT NOT NULL DEFAULT '[]'
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts
            USING fts5(title, content, tags, content='documents', content_rowid='id');
            """
        )
        _seed_documents(conn)


def _seed_documents(conn: sqlite3.Connection) -> None:
    if not SEED_DOCS_DIR.exists():
        return

    for path in sorted(SEED_DOCS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = _title_from_markdown(text, path.stem)
        tags = _tags_from_markdown(text)
        conn.execute(
            """
            INSERT INTO documents (slug, title, content, tags_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
              title=excluded.title,
              content=excluded.content,
              tags_json=excluded.tags_json
            """,
            (path.stem, title, text, json.dumps(tags)),
        )
        row = conn.execute("SELECT id FROM documents WHERE slug = ?", (path.stem,)).fetchone()
        if row:
            conn.execute("DELETE FROM documents_fts WHERE rowid = ?", (row["id"],))
            conn.execute(
                "INSERT INTO documents_fts(rowid, title, content, tags) VALUES (?, ?, ?, ?)",
                (row["id"], title, text, " ".join(tags)),
            )


def _title_from_markdown(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback.replace("-", " ").title()


def _tags_from_markdown(text: str) -> list[str]:
    for line in text.splitlines():
        if line.lower().startswith("tags:"):
            return [part.strip() for part in line.split(":", 1)[1].split(",") if part.strip()]
    return []


def create_case(payload: dict[str, Any]) -> int:
    now = utc_now()
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO cases
              (source, title, body, error_logs, environment, product_area, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'analyzing', ?, ?)
            """,
            (
                payload["source"],
                payload["title"],
                payload["body"],
                payload.get("error_logs", ""),
                payload.get("environment", ""),
                payload.get("product_area", ""),
                now,
                now,
            ),
        )
        return int(cur.lastrowid)


def save_case_output(case_id: int, output: AgentOutput, raw_json: dict[str, Any]) -> None:
    now = utc_now()
    tags_json = json.dumps(output.tags)
    steps_json = json.dumps([step.model_dump() for step in output.troubleshooting_steps])
    with connect() as conn:
        conn.execute(
            """
            UPDATE cases
            SET status='analyzed', category=?, priority=?, tags_json=?, updated_at=?
            WHERE id=?
            """,
            (output.category, output.priority, tags_json, now, case_id),
        )
        conn.execute(
            """
            INSERT INTO case_outputs
              (case_id, provider, model, summary, customer_reply, troubleshooting_json,
               kb_markdown, internal_notes, raw_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(case_id) DO UPDATE SET
              provider=excluded.provider,
              model=excluded.model,
              summary=excluded.summary,
              customer_reply=excluded.customer_reply,
              troubleshooting_json=excluded.troubleshooting_json,
              kb_markdown=excluded.kb_markdown,
              internal_notes=excluded.internal_notes,
              raw_json=excluded.raw_json,
              created_at=excluded.created_at
            """,
            (
                case_id,
                output.provider,
                output.model,
                output.summary,
                output.customer_reply,
                steps_json,
                output.kb_article,
                output.internal_notes,
                json.dumps(raw_json),
                now,
            ),
        )


def mark_case_failed(case_id: int) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE cases SET status='failed', updated_at=? WHERE id=?",
            (utc_now(), case_id),
        )


def list_cases(limit: int = 25) -> list[CaseListItem]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, title, source, status, category, priority, tags_json, created_at, updated_at
            FROM cases
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        CaseListItem(
            id=row["id"],
            title=row["title"],
            source=row["source"],
            status=row["status"],
            category=row["category"],
            priority=row["priority"],
            tags=_json_list(row["tags_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


def get_case(case_id: int) -> CaseRecord | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        output_row = conn.execute("SELECT * FROM case_outputs WHERE case_id = ?", (case_id,)).fetchone()
    if not row:
        return None
    return _case_record(row, output_row)


def _case_record(row: sqlite3.Row, output_row: sqlite3.Row | None) -> CaseRecord:
    output = None
    if output_row:
        output = AgentOutput(
            summary=output_row["summary"],
            category=row["category"] or "Other",
            priority=row["priority"] or "medium",
            customer_reply=output_row["customer_reply"],
            troubleshooting_steps=[
                TroubleshootingStep(**item) for item in _json_list(output_row["troubleshooting_json"])
            ],
            kb_article=output_row["kb_markdown"],
            internal_notes=output_row["internal_notes"],
            tags=_json_list(row["tags_json"]),
            provider=output_row["provider"],
            model=output_row["model"],
        )
    return CaseRecord(
        id=row["id"],
        source=row["source"],
        title=row["title"],
        body=row["body"],
        environment=row["environment"],
        product_area=row["product_area"],
        status=row["status"],
        category=row["category"],
        priority=row["priority"],
        tags=_json_list(row["tags_json"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        output=output,
    )


def save_kb_article(case_id: int, title: str, category: str, markdown: str) -> KbArticle:
    now = utc_now()
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO kb_articles (title, category, markdown, source_case_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, category, markdown, case_id, now),
        )
        article_id = int(cur.lastrowid)
    article = get_kb_article(article_id)
    if article is None:
        raise RuntimeError("Failed to save knowledge base article.")
    return article


def list_kb_articles(query: str = "", limit: int = 30) -> list[KbArticle]:
    sql = """
        SELECT id, title, category, markdown, source_case_id, created_at
        FROM kb_articles
    """
    params: tuple[Any, ...]
    if query:
        sql += " WHERE title LIKE ? OR markdown LIKE ? OR category LIKE ?"
        like = f"%{query}%"
        params = (like, like, like, limit)
    else:
        params = (limit,)
    sql += " ORDER BY id DESC LIMIT ?"
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_kb_article(row) for row in rows]


def get_kb_article(article_id: int) -> KbArticle | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT id, title, category, markdown, source_case_id, created_at FROM kb_articles WHERE id=?",
            (article_id,),
        ).fetchone()
    return _kb_article(row) if row else None


def _kb_article(row: sqlite3.Row) -> KbArticle:
    return KbArticle(
        id=row["id"],
        title=row["title"],
        category=row["category"],
        markdown=row["markdown"],
        source_case_id=row["source_case_id"],
        created_at=row["created_at"],
    )


def _json_list(value: str | None) -> list[Any]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []
