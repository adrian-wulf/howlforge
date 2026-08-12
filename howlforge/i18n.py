"""Localisation for HowlForge.

Two layers exist:
* **Vocabulary keys** (status, priority, category, type...) are English tokens and
  are *never* translated - Dataview, filters and the web panel depend on them.
* **Labels and UI strings** here are translated and used for display, CLI output,
  and as hints in AI prompts so the AI writes note *content* in the chosen language.

``LANG_DEFAULT`` is the fallback when a label is missing.
"""

from __future__ import annotations

from typing import Dict

LANG_DEFAULT = "en"
SUPPORTED = ["pl", "en"]

# ---- Vocabulary key -> display label ---------------------------------------
# Only keys present in the vocabulary are allowed to appear here.

STATUS_LABELS: Dict[str, Dict[str, str]] = {
    "raw": {"en": "Raw", "pl": "Surowe"},
    "processed": {"en": "Processed", "pl": "Przetworzone"},
    "prototype": {"en": "Prototype", "pl": "Prototyp"},
    "implemented": {"en": "Implemented", "pl": "Zaimplementowane"},
    "rejected": {"en": "Rejected", "pl": "Odrzucone"},
    "archived": {"en": "Archived", "pl": "Zarchiwizowane"},
}

PRIORITY_LABELS: Dict[str, Dict[str, str]] = {
    "critical": {"en": "Critical", "pl": "Krytyczny"},
    "high": {"en": "High", "pl": "Wysoki"},
    "medium": {"en": "Medium", "pl": "Średni"},
    "low": {"en": "Low", "pl": "Niski"},
    "backlog": {"en": "Backlog", "pl": "Backlog"},
}

TYPE_LABELS: Dict[str, Dict[str, str]] = {
    "idea": {"en": "Idea", "pl": "Pomysł"},
    "mechanic": {"en": "Mechanic", "pl": "Mechanika"},
    "system": {"en": "System", "pl": "System"},
    "asset": {"en": "Asset", "pl": "Asset"},
    "reference": {"en": "Reference", "pl": "Referencja"},
    "inspiration": {"en": "Inspiration", "pl": "Inspiracja"},
    "gdd": {"en": "GDD", "pl": "GDD"},
    "synthesis": {"en": "Synthesis", "pl": "Synteza"},
    "note": {"en": "Note", "pl": "Notatka"},
}

SOURCE_LABELS: Dict[str, Dict[str, str]] = {
    "telegram": {"en": "Telegram", "pl": "Telegram"},
    "manual": {"en": "Manual", "pl": "Ręcznie"},
    "web": {"en": "Web", "pl": "Web"},
    "voice": {"en": "Voice", "pl": "Głos"},
    "image": {"en": "Image", "pl": "Obraz"},
    "api": {"en": "API", "pl": "API"},
    "import": {"en": "Import", "pl": "Import"},
}

CATEGORY_LABELS: Dict[str, Dict[str, str]] = {
    "art": {"en": "Art", "pl": "Art"},
    "gameplay": {"en": "Gameplay", "pl": "Gameplay"},
    "mechanics": {"en": "Mechanics", "pl": "Mechaniki"},
    "audio": {"en": "Audio", "pl": "Audio"},
    "story": {"en": "Story", "pl": "Fabuła"},
    "systems": {"en": "Systems", "pl": "Systemy"},
    "technical": {"en": "Technical", "pl": "Technika"},
    "production": {"en": "Production", "pl": "Produkcja"},
    "monetization": {"en": "Monetization", "pl": "Monetyzacja"},
    "marketing": {"en": "Marketing", "pl": "Marketing"},
    "misc": {"en": "Misc", "pl": "Różne"},
}

_FIELD_LABELS: Dict[str, Dict[str, str]] = {
    "type": {"en": "Type", "pl": "Typ"},
    "project": {"en": "Project", "pl": "Projekt"},
    "category": {"en": "Category", "pl": "Kategoria"},
    "subcategory": {"en": "Subcategory", "pl": "Podkategoria"},
    "status": {"en": "Status", "pl": "Status"},
    "priority": {"en": "Priority", "pl": "Priorytet"},
    "tags": {"en": "Tags", "pl": "Tagi"},
    "related": {"en": "Related", "pl": "Powiązane"},
    "created": {"en": "Created", "pl": "Utworzono"},
    "source": {"en": "Source", "pl": "Źródło"},
}


def _pick(labels: Dict[str, Dict[str, str]], key: str, lang: str) -> str:
    if lang not in SUPPORTED:
        lang = LANG_DEFAULT
    return labels.get(key, {}).get(lang, labels.get(key, {}).get(LANG_DEFAULT, key))


def status_label(key: str, lang: str = LANG_DEFAULT) -> str:
    return _pick(STATUS_LABELS, key, lang)


def priority_label(key: str, lang: str = LANG_DEFAULT) -> str:
    return _pick(PRIORITY_LABELS, key, lang)


def type_label(key: str, lang: str = LANG_DEFAULT) -> str:
    return _pick(TYPE_LABELS, key, lang)


def source_label(key: str, lang: str = LANG_DEFAULT) -> str:
    return _pick(SOURCE_LABELS, key, lang)


def category_label(key: str, lang: str = LANG_DEFAULT) -> str:
    return _pick(CATEGORY_LABELS, key, lang)


def field_label(key: str, lang: str = LANG_DEFAULT) -> str:
    return _pick(_FIELD_LABELS, key, lang)


def normalize_lang(lang: str | None) -> str:
    """Return a supported language code, falling back to the default."""
    if lang in SUPPORTED:
        return lang
    return LANG_DEFAULT
