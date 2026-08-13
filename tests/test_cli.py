from howlforge import categories as categories_mod
from howlforge import cli
from howlforge.config import Settings


class FakeClient:
    available_models = ["howl-classify"]

    def __init__(self, output):
        self.output = output
        self.prompt = ""

    def complete(self, messages, model=None, **kwargs):
        self.prompt = messages[-1]["content"] if messages else ""
        return self.output


def test_classify_with_vault_passes_descriptions(tmp_path, monkeypatch):
    categories_mod.add(tmp_path, "Ksiazki", description="Ksiazki do przeczytania.")
    fake = FakeClient(
        '{"type": "note", "category": "ksiazki", "subcategory": "none", '
        '"status": "raw", "priority": "medium", "tags": ["reading"], '
        '"related": [], "title": "Deep work", "summary": "Read Deep Work."}'
    )
    monkeypatch.setattr(cli, "LLMClient", lambda *a, **k: fake)
    settings = Settings(language="pl", vault_path=tmp_path, llm_model="howl-classify")
    note = cli._classify_with_vault("Read Deep Work", settings, "pl")
    assert note.category == "ksiazki"
    assert "Ksiazki do przeczytania." in fake.prompt
