"""Configuration for HowlForge.

``Settings`` is a plain dataclass with sensible defaults and no side effects, so
it can be constructed freely in tests. Env / ``.env`` is read only in
:func:`get_settings`, which is what the app uses.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .i18n import normalize_lang

_DEFAULT_VAULT = Path("vault")
_DEFAULT_LLM_CONFIG = Path("howlforge/llm_config.yaml")


@dataclass
class Settings:
    language: str = "pl"
    vault_path: Path = _DEFAULT_VAULT
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    llm_model: str = "howl-classify"
    llm_config: Path = _DEFAULT_LLM_CONFIG
    panel_password: str = ""


def get_settings() -> Settings:
    """Build settings from the environment / ``.env`` file."""
    load_dotenv()
    return Settings(
        language=normalize_lang(os.getenv("HOWLFORGE_LANGUAGE", "pl")),
        vault_path=Path(os.getenv("HOWLFORGE_VAULT_PATH", "vault")),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        llm_model=os.getenv("HOWLFORGE_LLM_MODEL", "howl-classify"),
        llm_config=Path(os.getenv("HOWLFORGE_LLM_CONFIG", "howlforge/llm_config.yaml")),
        panel_password=os.getenv("HOWLFORGE_PANEL_PASSWORD", ""),
    )
