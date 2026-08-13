"""Extensible note categories.

Built-in categories live in :mod:`howlforge.vocabulary` (the controlled default
set). Users can add their own categories at runtime - from the panel or the bot -
which are stored per-vault at ``<vault>/.howlforge/categories.json`` and merged
over the defaults. Custom categories are validated with the same rules so nothing
breaks the vocabulary contract.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from . import vocabulary

_FILENAME = "categories.json"


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()


def _path(vault_root: Path) -> Path:
    return Path(vault_root) / ".howlforge" / _FILENAME


def load(vault_root: Path) -> Dict[str, List[str]]:
    """Load custom categories from the vault file (empty dict if none).

    Each entry is either a list of subcategories (legacy format) or an object
    with ``subcategories`` and an optional ``description``:
    ``{"books": ["fiction", "nonfiction"]}`` or
    ``{"books": {"subcategories": ["fiction"], "description": "Books to read."}}``.
    Only the subcategories are returned here; see :func:`load_descriptions`.
    """
    p = _path(vault_root)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    result: Dict[str, List[str]] = {}
    for k, v in data.items():
        if isinstance(v, list):
            result[k] = [s for s in v if isinstance(s, str)]
        elif isinstance(v, dict):
            subs = v.get("subcategories", ["none"])
            if isinstance(subs, list):
                result[k] = [s for s in subs if isinstance(s, str)] or ["none"]
    return result


def load_descriptions(vault_root: Path) -> Dict[str, str]:
    """Load custom category descriptions from the vault file (empty dict if none)."""
    p = _path(vault_root)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: Dict[str, str] = {}
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(v.get("description"), str):
            desc = v["description"].strip()
            if desc:
                out[k] = desc
    return out


def save(vault_root: Path, custom: Dict[str, List[str]]) -> None:
    p = _path(vault_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(custom, indent=2, ensure_ascii=False), encoding="utf-8")


def add(
    vault_root: Path,
    name: str,
    subcategories: List[str] | None = None,
    description: str | None = None,
) -> str:
    """Add a new custom category and return its slug.

    An optional ``description`` is stored next to the subcategories and is shown
    to the LLM during classification so notes get assigned to the right category.

    Raises :class:`ValueError` for empty/duplicate names (including collisions
    with built-in categories).
    """
    name = _slug(name)
    if not name:
        raise ValueError("Category name cannot be empty.")
    if name in vocabulary.CATEGORIES:
        raise ValueError(f"Category '{name}' already exists (built-in).")
    custom = load(vault_root)
    if name in custom:
        raise ValueError(f"Category '{name}' already exists.")
    subs = [_slug(s) for s in (subcategories or []) if _slug(s)]
    desc = (description or "").strip()
    if desc:
        custom[name] = {"subcategories": subs or ["none"], "description": desc}
    else:
        custom[name] = subs or ["none"]
    save(vault_root, custom)
    return name


def remove(vault_root: Path, name: str) -> bool:
    """Remove a custom category. Built-in categories cannot be removed.

    Returns ``True`` if the category was removed, ``False`` if it did not exist.
    Raises :class:`ValueError` for built-in categories.
    """
    name = _slug(name)
    if name in vocabulary.CATEGORIES:
        raise ValueError(f"Built-in category '{name}' cannot be removed.")
    custom = load(vault_root)
    if name not in custom:
        return False
    del custom[name]
    save(vault_root, custom)
    return True


def all_categories(vault_root: Optional[Path] = None) -> Dict[str, List[str]]:
    """Return built-in categories merged with the vault's custom categories."""
    merged = dict(vocabulary.CATEGORIES)
    if vault_root is not None:
        merged.update(load(vault_root))
    return merged


def is_valid_category(name: str, vault_root: Optional[Path] = None) -> bool:
    return name in all_categories(vault_root)


def is_valid_subcategory(
    category: str,
    subcategory: str,
    vault_root: Optional[Path] = None,
) -> bool:
    return subcategory in all_categories(vault_root).get(category, [])


def merged_descriptions(vault_root: Path, lang: str = "en") -> Dict[str, str]:
    """Return category descriptions for the classification prompt.

    Built-in descriptions come from :mod:`howlforge.i18n` in the chosen language;
    per-vault custom descriptions (if any) are merged over them.
    """
    from .i18n import category_description, normalize_lang

    lang = normalize_lang(lang)
    merged: Dict[str, str] = {}
    for cat in vocabulary.CATEGORIES:
        desc = category_description(cat, lang)
        if desc:
            merged[cat] = desc
    merged.update(load_descriptions(vault_root))
    return merged
