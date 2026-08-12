"""Configuration for HowlForge.

Reads from environment / ``.env``. Pydantic-settings style without the extra dep;
we use plain os.environ + dotenv for simplicity.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
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
    # Store overrides separately to avoid mutating defaults across instances.
    _env_loaded: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        if not self._env_loaded:
            load_dotenv()
            self.language = normalize_lang(os.getenv("HOWLFORGE_LANGUAGE", "pl"))
            self.vault_path = Path(os.getenv("HOWLFORGE_VAULT_PATH", "vault"))
            self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
            self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
            self.llm_model = os.getenv("HOWLFORGE_LLM_MODEL", "howl-classify")
            self.llm_config = Path(os.getenv("HOWLFORGE_LLM_CONFIG", "howlforge/llm_config.yaml"))
            self._env_loaded = True


def get_settings() -> Settings:
    return Settings()
