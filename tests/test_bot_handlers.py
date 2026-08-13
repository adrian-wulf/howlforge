"""Handler-level tests: drive bot handlers with a fake aiogram Message."""
import asyncio
from types import SimpleNamespace

from howlforge import bot as bot_mod
from howlforge import categories as categories_mod
from howlforge.config import Settings


class _FakeMessage:
    def __init__(self, text: str, sent: list):
        self.text = text
        self.chat = SimpleNamespace(id=7)
        self.from_user = SimpleNamespace(id=7)
        self._sent = sent

    async def answer(self, text="", **kwargs):
        self._sent.append(text)


class RecordingClient:
    available_models = ["howl-classify"]

    def __init__(self, output: str):
        self.output = output
        self.prompt = ""

    def complete(self, messages, model=None, **kwargs):
        self.prompt = messages[-1]["content"] if messages else ""
        return self.output


def _run(coro):
    return asyncio.run(coro)


def test_on_newcat_handler_saves_description(tmp_path, monkeypatch):
    settings = Settings(language="pl", vault_path=tmp_path)
    monkeypatch.setattr(bot_mod, "get_settings", lambda: settings)
    sent: list = []
    _run(bot_mod.on_newcat(_FakeMessage("/newcat Ksiazki recenzje | Ksiazki do przeczytania.", sent)))
    assert categories_mod.load(tmp_path) == {"ksiazki": ["recenzje"]}
    assert categories_mod.load_descriptions(tmp_path) == {"ksiazki": "Ksiazki do przeczytania."}
    assert any("ksiazki" in s for s in sent)


def test_await_category_flow_saves_description(tmp_path, monkeypatch):
    settings = Settings(language="pl", vault_path=tmp_path)
    monkeypatch.setattr(bot_mod, "get_settings", lambda: settings)
    sent: list = []
    msg = _FakeMessage("Ksiazki recenzje | Opis ksiazek.", sent)
    bot_mod._set_flow(msg, step="await_category")
    _run(bot_mod.on_text(msg))
    assert categories_mod.load(tmp_path) == {"ksiazki": ["recenzje"]}
    assert categories_mod.load_descriptions(tmp_path) == {"ksiazki": "Opis ksiazek."}
    assert any("ksiazki" in s for s in sent)


def test_free_text_capture_passes_descriptions(tmp_path, monkeypatch):
    categories_mod.add(tmp_path, "Ksiazki", description="Ksiazki do przeczytania.")
    settings = Settings(language="pl", vault_path=tmp_path, llm_model="howl-classify")
    monkeypatch.setattr(bot_mod, "get_settings", lambda: settings)
    client = RecordingClient(
        '{"type": "note", "category": "ksiazki", "subcategory": "none", '
        '"status": "raw", "priority": "medium", "tags": ["reading"], '
        '"related": [], "title": "Deep work", "summary": "Read Deep Work."}'
    )
    monkeypatch.setattr("howlforge.capture.LLMClient", lambda *a, **k: client)
    sent: list = []
    _run(bot_mod.on_text(_FakeMessage("Przeczytac Deep Work", sent)))
    assert "Ksiazki do przeczytania." in client.prompt
    assert any("Deep work" in s or "deep-work" in s for s in sent)
    assert (tmp_path / "00 Inbox" / "deep-work.md").exists()
