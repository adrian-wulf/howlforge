"""Classification pipeline: raw text -> validated Note.

Flow: build prompt (per language) -> LLM -> parse JSON -> validate against the
controlled vocabulary -> return a :class:`Note`. The pipeline never writes files;
callers decide where to persist.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from jinja2 import Environment, PackageLoader

from . import vocabulary
from .i18n import normalize_lang
from .llm import LLMClient
from .schema import Note

logger = logging.getLogger(__name__)

_PROMPTS = Environment(loader=PackageLoader("howlforge", "prompts"))


class ClassifyError(RuntimeError):
    """Raised when the LLM output cannot be turned into a valid note."""


def _build_context(lang: str) -> Dict[str, str]:
    cats = ", ".join(
        f"{cat}({', '.join(subs)})" for cat, subs in vocabulary.CATEGORIES.items()
    )
    return {
        "types": ", ".join(vocabulary.NOTE_TYPES),
        "statuses": ", ".join(vocabulary.STATUSES),
        "priorities": ", ".join(vocabulary.PRIORITIES),
        "categories": cats,
        "language": "English" if lang == "en" else "polski",
        "raw_text": "",
    }


def build_prompt(raw_text: str, lang: str) -> str:
    lang = normalize_lang(lang)
    template = _PROMPTS.get_template(f"classify_{lang}.j2")
    ctx = _build_context(lang)
    ctx["raw_text"] = raw_text
    return template.render(**ctx)


def build_messages(raw_text: str, lang: str) -> List[Dict[str, str]]:
    lang = normalize_lang(lang)
    system = (
        "You are a precise JSON-only assistant. Never wrap output in code fences."
        if lang == "en"
        else (
            "Jesteś precyzyjnym asystentem zwracającym wyłącznie JSON. "
            "Nigdy nie otaczaj wyniku znacznikami."
        )
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": build_prompt(raw_text, lang)},
    ]


def _extract_json(text: str) -> Dict[str, Any]:
    """Pull the first JSON object out of model output, tolerating fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Fall back to the first {...} block.
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ClassifyError("No JSON object found in model output.")
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ClassifyError(f"Could not parse JSON from model output: {exc}") from exc
    if not isinstance(data, dict):
        raise ClassifyError("Model output JSON is not an object.")
    return data


def _slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()


def data_to_note(data: Dict[str, Any], lang: str) -> Note:
    """Map validated LLM JSON onto a Note, coercing bad enums to safe defaults."""
    lang = normalize_lang(lang)
    note = Note()

    note.type = data.get("type") if data.get("type") in vocabulary.NOTE_TYPES else "idea"
    note.category = (
        data.get("category") if data.get("category") in vocabulary.CATEGORIES else "misc"
    )
    sub = data.get("subcategory", "none")
    note.subcategory = sub if sub in vocabulary.CATEGORIES[note.category] else "none"
    note.status = (
        data.get("status") if data.get("status") in vocabulary.STATUSES else "raw"
    )
    note.priority = (
        data.get("priority") if data.get("priority") in vocabulary.PRIORITIES else "backlog"
    )
    note.tags = [
        _slugify(t) for t in (data.get("tags") or []) if isinstance(t, str)
    ][:6]
    note.related = [
        str(r) for r in (data.get("related") or []) if isinstance(r, str)
    ][:8]
    note.project = _slugify(data["project"]) if data.get("project") else None
    note.title = _slugify(data.get("title") or "untitled")
    note.body = (data.get("summary") or "").strip()
    note.language = lang
    return note


def classify(
    raw_text: str,
    client: LLMClient,
    lang: str,
    model: Optional[str] = None,
) -> Note:
    """Classify raw text into a validated Note using the given LLM client."""
    if not raw_text.strip():
        raise ClassifyError("Cannot classify empty text.")
    messages = build_messages(raw_text, lang)
    output = client.complete(messages, model=model)
    data = _extract_json(output)
    note = data_to_note(data, lang)
    errors = note.validate()
    if errors:
        logger.warning("Note validated with corrections: %s", errors)
    return note
