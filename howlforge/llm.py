"""Provider-agnostic LLM client built on LiteLLM.

LiteLLM gives one OpenAI-compatible interface over 100+ providers (Claude, Gemini,
GPT, DeepSeek, NVIDIA NIM, OpenRouter...). Models are declared in
``llm_config.yaml``; the code never hardcodes a provider. Multiple entries may share
the same ``model_name`` so LiteLLM's Router can fail over automatically.

The default config uses NVIDIA NIM (free tier) so the tool works at $0 out of the box.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from litellm import Router

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path("howlforge/llm_config.yaml")


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, config_path: Path = DEFAULT_CONFIG, default_model: str = "howl-classify"):
        self.default_model = default_model
        self.config_path = Path(config_path)
        self.router = self._build_router(self.config_path)

    def _build_router(self, path: Path) -> Router:
        if not path.exists():
            logger.warning("LLM config %s not found; using a stub router (offline mode).", path)
            return Router(model_list=[])
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        model_list = data.get("model_list", [])
        if not model_list:
            logger.warning("LLM config %s has an empty model_list.", path)
        return Router(model_list=model_list)

    @property
    def available_models(self) -> List[str]:
        return [m.get("model_name") for m in self.router.model_list if m.get("model_name")]

    def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Run a chat completion and return the text content.

        Args:
            messages: OpenAI-style ``[{"role": ..., "content": ...}]`` list.
            model: the ``model_name`` key from ``llm_config.yaml``. Defaults to
                ``self.default_model``.
        """
        model_key = model or self.default_model
        if model_key not in self.available_models:
            raise LLMError(
                f"Model key '{model_key}' is not in {self.config_path}. "
                f"Available: {self.available_models or 'none (config empty)'}."
            )
        try:
            resp = self.router.completion(model=model_key, messages=messages, **kwargs)
        except Exception as exc:  # noqa: BLE001 - surface as our own error
            raise LLMError(f"LLM call failed for '{model_key}': {exc}") from exc

        try:
            return resp.choices[0].message.content.strip()  # type: ignore[union-attr]
        except (AttributeError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected LLM response shape for '{model_key}': {exc}") from exc

    def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """Return a dense embedding vector for ``text`` via the configured model.

        The default model key is ``howl-embed``. Raises :class:`LLMError` if the
        key is missing from the config or the provider call fails.
        """
        model_key = model or "howl-embed"
        if model_key not in self.available_models:
            raise LLMError(
                f"Embedding model key '{model_key}' is not in {self.config_path}. "
                f"Available: {self.available_models or 'none (config empty)'}."
            )
        try:
            resp = self.router.embeddings(model=model_key, input=[text])
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Embedding call failed for '{model_key}': {exc}") from exc
        try:
            return list(resp.data[0]["embedding"])  # type: ignore[index]
        except (AttributeError, IndexError, TypeError, KeyError) as exc:
            raise LLMError(f"Unexpected embedding response shape: {exc}") from exc
