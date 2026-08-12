import pytest

from howlforge.schema import Note
from howlforge.synthesize import (
    SynthesisError,
    build_synthesis_prompt,
    collect_notes,
    synthesize,
)


class FakeClient:
    available_models = ["howl-synthesize"]

    def __init__(self, output: str):
        self.output = output

    def complete(self, messages, model=None):
        return self.output


def _note_md(title: str, created: str, status: str = "raw", body: str = "x", **kw) -> str:
    fm = {
        "title": title,
        "type": "idea",
        "category": "gameplay",
        "subcategory": "loop",
        "status": status,
        "priority": "medium",
        "tags": [],
        "created": created,
        "body": body,
        **kw,
    }
    return Note(**fm).to_markdown()


def test_collect_filters_rejected_and_old(tmp_path):
    recent = "2026-08-11T10:00:00Z"
    old = "2020-01-01T10:00:00Z"
    (tmp_path / "a.md").write_text(_note_md("Good", recent), encoding="utf-8")
    (tmp_path / "b.md").write_text(
        _note_md("Rejected", recent, status="rejected"), encoding="utf-8"
    )
    (tmp_path / "c.md").write_text(_note_md("Old", old), encoding="utf-8")

    notes = collect_notes(tmp_path, days=30)
    titles = {n.title for n, _ in notes}
    assert "Good" in titles
    assert "Rejected" not in titles
    assert "Old" not in titles


def test_collect_filters_project(tmp_path):
    (tmp_path / "a.md").write_text(
        _note_md("Wolf", "2026-08-11T10:00:00Z", project="wolfpack"), encoding="utf-8"
    )
    (tmp_path / "b.md").write_text(
        _note_md("Farm", "2026-08-11T10:00:00Z", project="cowboy-farm"), encoding="utf-8"
    )
    notes = collect_notes(tmp_path, days=30, project="wolfpack")
    assert [n.title for n, _ in notes] == ["Wolf"]


def test_build_synthesis_prompt_pl(tmp_path):
    (tmp_path / "a.md").write_text(
        _note_md("Wolf", "2026-08-11T10:00:00Z"), encoding="utf-8"
    )
    notes = collect_notes(tmp_path, days=30)
    prompt = build_synthesis_prompt(notes, "pl", digest_title="Tygodniowe podsumowanie")
    assert "Jesteś HowlForge" in prompt
    assert "polski" in prompt
    assert "Wolf" in prompt


def test_synthesize_writes_append_only(tmp_path):
    (tmp_path / "a.md").write_text(
        _note_md("Wolf", "2026-08-11T10:00:00Z"), encoding="utf-8"
    )
    client = FakeClient("## Tygodniowe podsumowanie\n### Kluczowe pomysły\n- wilk")
    p1 = synthesize(tmp_path, client, "pl", days=30)
    p2 = synthesize(tmp_path, client, "pl", days=30)
    assert p1.exists() and p2.exists()
    assert p1 != p2  # append-only: each run creates a new file
    note = Note.from_markdown(p1.read_text(encoding="utf-8"))
    assert note.type == "synthesis"
    assert note.generated is True


def test_synthesize_no_notes_raises(tmp_path, monkeypatch):
    client = FakeClient("x")
    with pytest.raises(SynthesisError):
        synthesize(tmp_path, client, "pl", days=30)
