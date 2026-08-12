"""Semantic search over the vault.

A lightweight vector index stored in SQLite (stdlib, no native extension needed).
Notes are embedded with the provider-agnostic LiteLLM client (``howl-embed`` model)
and stored as JSON vectors. Queries are embedded the same way and ranked by cosine
similarity.

Two commands:
* ``index_vault`` - (re)build the index for all notes in the vault.
* ``search``     - rank notes against a query.

The index lives at ``<vault>/.howlforge/embeddings.db`` and is not a Markdown file,
so it is excluded from Obsidian and the note listing.
"""

from __future__ import annotations

import json
import logging
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .llm import LLMClient
from .schema import Note
from .vault import list_notes

logger = logging.getLogger(__name__)


class SearchError(RuntimeError):
    pass


def _index_path(vault_root: Path) -> Path:
    return Path(vault_root) / ".howlforge" / "embeddings.db"


def _connect(vault_root: Path) -> sqlite3.Connection:
    db = _index_path(vault_root)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            path TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            vec TEXT NOT NULL,
            updated TEXT NOT NULL
        )
        """
    )
    return conn


def _normalize(v: List[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


def _cosine(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _text_for(note: Note) -> str:
    return f"{note.title}\n{note.body}".strip()


def index_vault(
    vault_root: Path,
    client: LLMClient,
    model: Optional[str] = None,
) -> int:
    """Embed every note in the vault and upsert it into the vector index.

    Returns the number of notes indexed.
    """
    conn = _connect(vault_root)
    count = 0
    try:
        for path in list_notes(vault_root):
            note = Note.from_markdown(path.read_text(encoding="utf-8"))
            vec = _normalize(client.embed(_text_for(note), model))
            rel = str(path.relative_to(vault_root))
            conn.execute(
                """
                INSERT INTO embeddings (path, title, body, vec, updated)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    title=excluded.title, body=excluded.body,
                    vec=excluded.vec, updated=excluded.updated
                """,
                (rel, note.title, note.body, json.dumps(vec), note.updated),
            )
            count += 1
        conn.commit()
    finally:
        conn.close()
    logger.info("Indexed %d notes in %s", count, vault_root)
    return count


@dataclass
class SearchHit:
    path: str
    title: str
    score: float


def search(
    vault_root: Path,
    client: LLMClient,
    query: str,
    k: int = 5,
    model: Optional[str] = None,
) -> List[SearchHit]:
    """Rank notes by similarity to ``query`` and return the top ``k``."""
    if not query.strip():
        raise SearchError("Empty search query.")
    conn = _connect(vault_root)
    qvec = _normalize(client.embed(query, model))
    hits: List[SearchHit] = []
    try:
        rows = conn.execute("SELECT path, title, vec FROM embeddings").fetchall()
    finally:
        conn.close()
    if not rows:
        raise SearchError("Index is empty. Run `howlforge index` first.")
    for rel, title, vec_json in rows:
        try:
            vec = _normalize(json.loads(vec_json))
        except (json.JSONDecodeError, TypeError):
            continue
        hits.append(SearchHit(path=rel, title=title, score=_cosine(qvec, vec)))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:k]
