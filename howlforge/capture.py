"""Capture service: the single entry point for "a raw idea arrives".

Used by both the Telegram bot and the HTTP API so the behaviour is identical:
classify -> validate -> save to the vault -> return the result for a reply.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import categories as categories_mod
from . import vocab as vocab_mod
from .classify import ClassifyError, classify
from .config import Settings
from .i18n import normalize_lang
from .llm import LLMClient, LLMError
from .schema import Note
from .vault import write_note

logger = logging.getLogger(__name__)


def _slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()


@dataclass
class CaptureResult:
    note: Note
    path: Path
    ok: bool = True
    error: str = ""


class CaptureError(RuntimeError):
    pass


def capture_manual(
    text: str,
    settings: Settings,
    *,
    project: Optional[str] = None,
    category: str = "misc",
    subcategory: str = "none",
    status: str = "raw",
    priority: str = "backlog",
    tags: Optional[list[str]] = None,
) -> CaptureResult:
    """Save a note directly from the panel without an AI call.

    ``text`` becomes the body; a short title is derived from it. This works with
    no API key configured.
    """
    text = text.strip()
    if not text:
        raise CaptureError("Empty capture text.")
    title = text.splitlines()[0].strip()
    if len(title) > 60:
        title = title[:60].rsplit(" ", 1)[0]
    note = Note(
        title=title,
        body=text,
        project=_slugify(project) if project else None,
        category=category,
        subcategory=subcategory,
        status=status,
        priority=priority,
        tags=[_slugify(t) for t in (tags or []) if t.strip()],
        source="manual",
        language=normalize_lang(settings.language),
    )
    cats = categories_mod.all_categories(settings.vault_path)
    statuses = vocab_mod.status_keys(settings.vault_path)
    priorities = vocab_mod.priority_keys(settings.vault_path)
    errors = note.validate(cats, statuses, priorities)
    if errors:
        raise CaptureError("; ".join(errors))
    path = write_note(note, settings.vault_path)
    return CaptureResult(note=note, path=path)


def capture(
    text: str,
    settings: Settings,
    client: LLMClient | None = None,
    project: Optional[str] = None,
) -> CaptureResult:
    """Classify, validate and save ``text``; return the note and its path.

    ``project`` overrides the AI-chosen project (useful when the user explicitly
    picked a project in the bot/panel).

    Raises :class:`CaptureError` when the text is empty or the LLM step fails.
    """
    if not text.strip():
        raise CaptureError("Empty capture text.")
    client = client or LLMClient(settings.llm_config, settings.llm_model)
    lang = normalize_lang(settings.language)
    cats = categories_mod.all_categories(settings.vault_path)
    statuses = vocab_mod.status_keys(settings.vault_path)
    priorities = vocab_mod.priority_keys(settings.vault_path)
    descriptions = categories_mod.merged_descriptions(settings.vault_path, lang)
    try:
        note = classify(
            text,
            client,
            lang,
            categories=cats,
            statuses=statuses,
            priorities=priorities,
            descriptions=descriptions,
        )
    except (LLMError, ClassifyError) as exc:
        raise CaptureError(str(exc)) from exc
    if project is not None:
        note.project = _slugify(project) or None
    path = write_note(note, settings.vault_path)
    return CaptureResult(note=note, path=path)


def reply_text(result: CaptureResult, lang: str) -> str:
    """Human-friendly confirmation, localised."""
    lang = normalize_lang(lang)
    note = result.note
    path = result.path
    if lang == "pl":
        return (
            f"Zapisano: **{note.title}**\n"
            f"Trafiło do: `{path}`\n"
            f"Typ: `{note.type}` | Kategoria: `{note.category}/{note.subcategory}`"
        )
    return (
        f"Saved: **{note.title}**\n"
        f"Filed under: `{path}`\n"
        f"Type: `{note.type}` | Category: `{note.category}/{note.subcategory}`"
    )
