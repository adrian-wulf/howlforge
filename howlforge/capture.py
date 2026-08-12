"""Capture service: the single entry point for "a raw idea arrives".

Used by both the Telegram bot and the HTTP API so the behaviour is identical:
classify -> validate -> save to the vault -> return the result for a reply.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .classify import ClassifyError, classify
from .config import Settings
from .i18n import normalize_lang
from .llm import LLMClient, LLMError
from .schema import Note
from .vault import write_note

logger = logging.getLogger(__name__)


@dataclass
class CaptureResult:
    note: Note
    path: Path
    ok: bool = True
    error: str = ""


class CaptureError(RuntimeError):
    pass


def capture(text: str, settings: Settings, client: LLMClient | None = None) -> CaptureResult:
    """Classify, validate and save ``text``; return the note and its path.

    Raises :class:`CaptureError` when the text is empty or the LLM step fails.
    """
    if not text.strip():
        raise CaptureError("Empty capture text.")
    client = client or LLMClient(settings.llm_config, settings.llm_model)
    lang = normalize_lang(settings.language)
    try:
        note = classify(text, client, lang)
    except (LLMError, ClassifyError) as exc:
        raise CaptureError(str(exc)) from exc
    path = write_note(note, settings.vault_path)
    return CaptureResult(note=note, path=path)


def reply_text(result: CaptureResult, lang: str) -> str:
    """Human-friendly confirmation, localised."""
    lang = normalize_lang(lang)
    note = result.note
    path = result.path
    if lang == "pl":
        return (
            f"✅ Zapisano: **{note.title}**\n"
            f"Trafiło do: `{path}`\n"
            f"Typ: `{note.type}` · Kategoria: `{note.category}/{note.subcategory}`"
        )
    return (
        f"✅ Saved: **{note.title}**\n"
        f"Filed under: `{path}`\n"
        f"Type: `{note.type}` · Category: `{note.category}/{note.subcategory}`"
    )
