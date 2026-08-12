"""Nightly AI synthesis: turn recent notes into an actionable digest.

Append-only by design: each run writes a brand-new synthesis note (never rewrites
source notes). The digest is a separate, clearly-marked ``generated: true`` file,
so AI output never touches your hand-written content.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from jinja2 import Environment, PackageLoader

from .classify import ClassifyError
from .i18n import normalize_lang
from .llm import LLMClient, LLMError
from .schema import Note
from .vault import list_notes

logger = logging.getLogger(__name__)

_PROMPTS = Environment(loader=PackageLoader("howlforge", "prompts"))

# Statuses that must be excluded from digests.
_EXCLUDED_STATUSES = {"rejected", "archived"}


class SynthesisError(RuntimeError):
    pass


def _parse_timestamp(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def collect_notes(
    vault_root: Path,
    days: int = 7,
    project: Optional[str] = None,
) -> List[Tuple[Note, Path]]:
    """Return recent, non-rejected notes, newest first."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    collected: List[Tuple[Note, Path]] = []
    for path in list_notes(vault_root):
        try:
            note = Note.from_markdown(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - skip unreadable files
            logger.warning("Skipping unreadable note %s: %s", path, exc)
            continue
        if note.status in _EXCLUDED_STATUSES:
            continue
        if project and (note.project or "").lower() != project.lower():
            continue
        if _parse_timestamp(note.created) < cutoff:
            continue
        collected.append((note, path))
    collected.sort(key=lambda t: _parse_timestamp(t[0].created), reverse=True)
    return collected


def _render_notes(notes: List[Tuple[Note, Path]]) -> str:
    blocks = []
    for note, _ in notes:
        blocks.append(
            f"### {note.title}  "
            f"(type: {note.type}, category: {note.category})\n{note.body}"
        )
    return "\n\n".join(blocks) if blocks else "No source notes in the window."


def build_synthesis_prompt(
    notes: List[Tuple[Note, Path]],
    lang: str,
    digest_title: str = "Weekly Digest",
) -> str:
    lang = normalize_lang(lang)
    template = _PROMPTS.get_template(f"synthesize_{lang}.j2")
    return template.render(
        language="English" if lang == "en" else "polski",
        digest_title=digest_title,
        notes=_render_notes(notes),
    )


def synthesize(
    vault_root: Path,
    client: LLMClient,
    lang: str,
    days: int = 7,
    project: Optional[str] = None,
    model: Optional[str] = None,
) -> Path:
    """Collect recent notes, ask the LLM for a digest, and save it append-only.

    Returns the path of the written synthesis note.
    """
    notes = collect_notes(vault_root, days, project)
    if not notes:
        raise SynthesisError("No notes in the window to synthesize.")

    prompt = build_synthesis_prompt(notes, lang)
    messages = [
        {"role": "system", "content": "You are a Markdown-only assistant."},
        {"role": "user", "content": prompt},
    ]
    try:
        digest = client.complete(messages, model=model)
    except (LLMError, ClassifyError) as exc:
        raise SynthesisError(str(exc)) from exc

    slug = (project or "global").lower().replace(" ", "-")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    note = Note(
        type="synthesis",
        project=project,
        category="production",
        subcategory="roadmap",
        status="processed",
        generated=True,
        language=normalize_lang(lang),
        title=f"{stamp}-{slug}-digest",
        body=digest.strip(),
    )
    from .vault import write_note

    return write_note(note, vault_root)
