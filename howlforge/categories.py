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
    """Load custom categories from the vault file (empty dict if none)."""
    p = _path(vault_root)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: [s for s in v if isinstance(s, str)] for k, v in data.items() if isinstance(v, list)}


def save(vault_root: Path, custom: Dict[str, List[str]]) -> None:
    p = _path(vault_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(custom, indent=2, ensure_ascii=False), encoding="utf-8")


def add(vault_root: Path, name: str, subcategories: List[str] | None = None) -> str:
    """Add a new custom category and return its slug.

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
