"""Extensible statuses and priorities (with labels + colors).

Built-ins come from :mod:`howlforge.vocabulary` (English keys). Users can add their
own statuses and priorities at runtime (from the panel), stored per-vault at
``<vault>/.howlforge/vocab.json``. Each entry carries an English + Polish label and a
color, so the Kanban board and filters can render them nicely.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from . import i18n, vocabulary

_FILENAME = "vocab.json"

# Default colors (hex) for built-in keys.
_STATUS_COLORS: Dict[str, str] = {
    "raw": "#d9b36b",
    "processed": "#7fc3d2",
    "prototype": "#c08ad9",
    "implemented": "#7fd29b",
    "rejected": "#d97f7f",
    "archived": "#9aa0aa",
}
_PRIORITY_COLORS: Dict[str, str] = {
    "critical": "#d97f7f",
    "high": "#d9a06b",
    "medium": "#d9c96b",
    "low": "#7fd29b",
    "backlog": "#9aa0aa",
}

# Simple single-character symbols (plain text, no emoji) for statuses and priorities.
_STATUS_SYMBOLS: Dict[str, str] = {
    "raw": "o",
    "processed": "~",
    "prototype": "*",
    "implemented": "V",
    "rejected": "x",
    "archived": "-",
}
_PRIORITY_SYMBOLS: Dict[str, str] = {
    "critical": "!!",
    "high": "!",
    "medium": "=",
    "low": "-",
    "backlog": ".",
}


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()


def _path(vault_root: Path) -> Path:
    return Path(vault_root) / ".howlforge" / _FILENAME


def load(vault_root: Path) -> Dict[str, List[dict]]:
    p = _path(vault_root)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        k: [e for e in v if isinstance(e, dict) and e.get("key")]
        for k, v in data.items()
        if k in ("statuses", "priorities") and isinstance(v, list)
    }


def save(vault_root: Path, data: Dict[str, List[dict]]) -> None:
    p = _path(vault_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _builtin_statuses() -> List[dict]:
    return [
        {
            "key": k,
            "label_en": i18n.status_label(k, "en"),
            "label_pl": i18n.status_label(k, "pl"),
            "color": _STATUS_COLORS.get(k, "#9aa0aa"),
            "symbol": _STATUS_SYMBOLS.get(k, "o"),
        }
        for k in vocabulary.STATUSES
    ]


def _builtin_priorities() -> List[dict]:
    return [
        {
            "key": k,
            "label_en": i18n.priority_label(k, "en"),
            "label_pl": i18n.priority_label(k, "pl"),
            "color": _PRIORITY_COLORS.get(k, "#9aa0aa"),
            "symbol": _PRIORITY_SYMBOLS.get(k, "o"),
        }
        for k in vocabulary.PRIORITIES
    ]


def _merge(builtin: List[dict], custom: List[dict]) -> List[dict]:
    seen = {e["key"] for e in builtin}
    merged = list(builtin)
    for e in custom:
        if e["key"] not in seen:
            merged.append(e)
            seen.add(e["key"])
    return merged


def all_statuses(vault_root: Optional[Path] = None) -> List[dict]:
    custom = load(vault_root).get("statuses", []) if vault_root is not None else []
    return _merge(_builtin_statuses(), custom)


def all_priorities(vault_root: Optional[Path] = None) -> List[dict]:
    custom = load(vault_root).get("priorities", []) if vault_root is not None else []
    return _merge(_builtin_priorities(), custom)


def status_keys(vault_root: Optional[Path] = None) -> List[str]:
    return [e["key"] for e in all_statuses(vault_root)]


def priority_keys(vault_root: Optional[Path] = None) -> List[str]:
    return [e["key"] for e in all_priorities(vault_root)]


def _add(vault_root: Path, kind: str, builtin_keys: List[str], entry: dict) -> str:
    key = _slug(entry.get("key", ""))
    if not key:
        raise ValueError("Name cannot be empty.")
    if key in builtin_keys:
        raise ValueError(f"'{key}' is a built-in {kind} and cannot be overridden.")
    data = load(vault_root)
    items = data.setdefault(kind, [])
    if any(e["key"] == key for e in items):
        raise ValueError(f"'{key}' already exists.")
    items.append(
        {
            "key": key,
            "label_en": entry.get("label_en") or key,
            "label_pl": entry.get("label_pl") or key,
            "color": entry.get("color") or "#9aa0aa",
            "symbol": entry.get("symbol") or "o",
        }
    )
    save(vault_root, data)
    return key


def add_status(
    vault_root: Path,
    key: str,
    label_en: Optional[str] = None,
    label_pl: Optional[str] = None,
    color: Optional[str] = None,
    symbol: Optional[str] = None,
) -> str:
    return _add(
        vault_root,
        "statuses",
        vocabulary.STATUSES,
        {"key": key, "label_en": label_en, "label_pl": label_pl, "color": color, "symbol": symbol},
    )


def add_priority(
    vault_root: Path,
    key: str,
    label_en: Optional[str] = None,
    label_pl: Optional[str] = None,
    color: Optional[str] = None,
    symbol: Optional[str] = None,
) -> str:
    return _add(
        vault_root,
        "priorities",
        vocabulary.PRIORITIES,
        {"key": key, "label_en": label_en, "label_pl": label_pl, "color": color, "symbol": symbol},
    )


def remove(vault_root: Path, kind: str, key: str) -> bool:
    if kind not in ("statuses", "priorities"):
        raise ValueError(f"Unknown vocab kind: {kind}")
    builtin = vocabulary.STATUSES if kind == "statuses" else vocabulary.PRIORITIES
    if key in builtin:
        raise ValueError(f"Built-in '{key}' cannot be removed.")
    data = load(vault_root)
    items = data.get(kind, [])
    remaining = [e for e in items if e["key"] != key]
    if len(remaining) == len(items):
        return False
    data[kind] = remaining
    save(vault_root, data)
    return True


def label(key: str, entries: List[dict], lang: str) -> str:
    for e in entries:
        if e["key"] == key:
            return e.get(f"label_{lang}") or e.get("label_en") or key
    return key


def color(key: str, entries: List[dict]) -> str:
    for e in entries:
        if e["key"] == key:
            return e.get("color") or "#9aa0aa"
    return "#9aa0aa"


def symbol(key: str, entries: List[dict]) -> str:
    for e in entries:
        if e["key"] == key:
            return e.get("symbol") or "o"
    return "o"
