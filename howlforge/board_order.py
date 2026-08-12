"""Persistent Kanban column order, per project.

Stores the category column order at ``<vault>/.howlforge/board_order.json``. If a
project has no saved order, categories fall back to their natural (vocabulary) order.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

_FILENAME = "board_order.json"


def _path(vault_root: Path) -> Path:
    return Path(vault_root) / ".howlforge" / _FILENAME


def load(vault_root: Path) -> Dict[str, List[str]]:
    p = _path(vault_root)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: [x for x in v if isinstance(x, str)] for k, v in data.items() if isinstance(v, list)}


def save(vault_root: Path, data: Dict[str, List[str]]) -> None:
    p = _path(vault_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_order(vault_root: Path, slug: str, default: List[str]) -> List[str]:
    """Return the saved column order for a project, appending any new categories."""
    saved = load(vault_root).get(slug, [])
    result = [c for c in saved if c in default]
    for c in default:
        if c not in result:
            result.append(c)
    return result


def move(
    vault_root: Path,
    slug: str,
    category: str,
    direction: int,
    default: List[str],
) -> List[str]:
    """Swap a column one place left (-1) or right (+1). Returns the new order."""
    order = get_order(vault_root, slug, default)
    if category not in order:
        return order
    i = order.index(category)
    j = i + direction
    if 0 <= j < len(order):
        order[i], order[j] = order[j], order[i]
    data = load(vault_root)
    data[slug] = order
    save(vault_root, data)
    return order
