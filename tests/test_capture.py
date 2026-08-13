from pathlib import Path

import pytest

from howlforge.capture import CaptureError, capture, capture_manual, reply_text
from howlforge.config import Settings


class FakeClient:
    available_models = ["howl-classify"]

    def __init__(self, output: str):
        self.output = output

    def complete(self, messages, model=None, **kwargs):
        return self.output


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        language="pl",
        vault_path=tmp_path,
        llm_model="howl-classify",
    )


def test_capture_saves_note(tmp_path):
    client = FakeClient(
        '{"type": "idea", "category": "gameplay", "subcategory": "loop", '
        '"status": "raw", "priority": "medium", "tags": ["farming"], '
        '"related": [], "title": "Night monsters", '
        '"summary": "Crops become monsters at night."}'
    )
    settings = _settings(tmp_path)
    result = capture("Crops become monsters at night", settings, client)
    assert result.ok
    assert result.note.title == "night-monsters"
    assert result.note.language == "pl"
    assert result.path.exists()


def test_capture_empty_raises(tmp_path):
    with pytest.raises(CaptureError):
        capture("   ", _settings(tmp_path), FakeClient("{}"))


def test_capture_manual_no_ai(tmp_path):
    settings = _settings(tmp_path)
    result = capture_manual(
        "A brand new idea about wolves",
        settings,
        project="Wolf Pack",
        category="gameplay",
        priority="high",
    )
    assert result.ok
    assert result.note.project == "wolf-pack"
    assert result.note.status == "raw"
    assert result.path.exists()


def test_capture_manual_empty_raises(tmp_path):
    with pytest.raises(CaptureError):
        capture_manual("   ", _settings(tmp_path))


def test_reply_text_pl(tmp_path):
    result = capture(
        "an idea",
        _settings(tmp_path),
        FakeClient(
            '{"type": "idea", "category": "misc", "status": "raw", '
            '"title": "x", "summary": "y"}'
        ),
    )
    reply = reply_text(result, "pl")
    assert "Zapisano" in reply
    assert "Trafiło do" in reply


def test_reply_text_en(tmp_path):
    result = capture(
        "an idea",
        _settings(tmp_path),
        FakeClient(
            '{"type": "idea", "category": "misc", "status": "raw", '
            '"title": "x", "summary": "y"}'
        ),
    )
    reply = reply_text(result, "en")
    assert "Saved" in reply
    assert "Filed under" in reply


class RecordingClient:
    available_models = ["howl-classify"]

    def __init__(self, output: str):
        self.output = output
        self.prompt = ""

    def complete(self, messages, model=None, **kwargs):
        self.prompt = messages[-1]["content"] if messages else ""
        return self.output


def test_capture_passes_category_descriptions_to_classifier(tmp_path):
    from howlforge import categories as categories_mod

    categories_mod.add(tmp_path, "Books", description="Books to read and review.")
    client = RecordingClient(
        '{"type": "note", "category": "books", "subcategory": "none", '
        '"status": "raw", "priority": "medium", "tags": ["reading"], '
        '"related": [], "title": "Read atomic habits", '
        '"summary": "Read Atomic Habits this month."}'
    )
    result = capture("Read Atomic Habits this month", _settings(tmp_path), client)
    assert result.ok
    assert result.note.category == "books"
    assert "Books to read and review." in client.prompt
