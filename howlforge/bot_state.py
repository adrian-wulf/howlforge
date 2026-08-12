"""Persistent per-chat state for the Telegram bot.

Stores the user's preferred language and default project in
``<vault>/.howlforge/bot_state.json`` so the bot remembers them across restarts.
Transient flow state (current step, chosen category) stays in memory in ``bot.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

_FILENAME = "bot_state.json"


def _path(vault_root: Path) -> Path:
    return Path(vault_root) / ".howlforge" / _FILENAME


def load(vault_root: Path) -> Dict[str, Dict[str, Any]]:
    p = _path(vault_root)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if isinstance(v, dict)}


def save(vault_root: Path, state: Dict[str, Dict[str, Any]]) -> None:
    p = _path(vault_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def get_user(vault_root: Path, chat_id: int) -> Dict[str, Any]:
    return load(vault_root).get(str(chat_id), {})


def set_user(vault_root: Path, chat_id: int, **fields: Any) -> Dict[str, Any]:
    state = load(vault_root)
    user = state.setdefault(str(chat_id), {})
    user.update(fields)
    save(vault_root, state)
    return user


def lang_of(vault_root: Path, chat_id: int, default: str) -> str:
    return str(get_user(vault_root, chat_id).get("lang") or default)


def project_of(vault_root: Path, chat_id: int) -> Optional[str]:
    value = get_user(vault_root, chat_id).get("project")
    return str(value) if value else None
