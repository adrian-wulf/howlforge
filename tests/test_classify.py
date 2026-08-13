import pytest

from howlforge.classify import (
    ClassifyError,
    _extract_json,
    build_prompt,
    classify,
    data_to_note,
)
from howlforge.schema import Note


class FakeClient:
    available_models = ["howl-classify"]

    def __init__(self, output: str):
        self.output = output

    def complete(self, messages, model=None, **kwargs):
        return self.output


def test_classify_pipeline_end_to_end():
    client = FakeClient(
        '```json\n'
        '{"type": "mechanic", "project": "Cowboy Farm", "category": "mechanics", '
        '"subcategory": "economy", "status": "raw", "priority": "high", '
        '"tags": ["economy"], "related": [], "title": "Dynamic pricing", '
        '"summary": "Prices shift with supply and demand."}\n```'
    )
    note = classify("idle farming economy", client, "pl")
    assert isinstance(note, Note)
    assert note.is_valid
    assert note.language == "pl"
    md = note.to_markdown()
    assert md.startswith("---\n")
    assert "dynamic-pricing" in md


def test_classify_empty_text_raises():
    client = FakeClient("{}")
    with pytest.raises(ClassifyError):
        classify("   ", client, "en")



def test_build_prompt_pl_contains_language():
    p = build_prompt("some idea", "pl")
    assert "Jesteś" in p
    assert "polski" in p
    assert "some idea" in p


def test_build_prompt_en_contains_language():
    p = build_prompt("some idea", "en")
    assert "You are HowlForge" in p
    assert "English" in p


def test_build_prompt_unknown_lang_falls_back():
    p = build_prompt("x", "de")
    assert "You are HowlForge" in p


def test_extract_json_plain():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_fenced():
    out = '```json\n{"a": 1}\n```'
    assert _extract_json(out) == {"a": 1}


def test_extract_json_embedded():
    out = 'Here you go: {"a": 1} thanks'
    assert _extract_json(out) == {"a": 1}


def test_extract_json_invalid():
    with pytest.raises(ClassifyError):
        _extract_json("no json here")


def test_data_to_note_maps_fields():
    data = {
        "type": "mechanic",
        "project": "Cowboy Farm",
        "category": "mechanics",
        "subcategory": "economy",
        "status": "raw",
        "priority": "high",
        "tags": ["economy", "cowboy"],
        "related": ["[[IdleFarming]]"],
        "title": "Dynamic pricing",
        "summary": "Prices shift with supply and demand.",
    }
    note = data_to_note(data, "en")
    assert isinstance(note, Note)
    assert note.type == "mechanic"
    assert note.project == "cowboy-farm"  # slugified
    assert note.category == "mechanics"
    assert note.subcategory == "economy"
    assert note.status == "raw"
    assert note.priority == "high"
    assert note.tags == ["economy", "cowboy"]
    assert note.title == "dynamic-pricing"  # slugified
    assert note.language == "en"


def test_data_to_note_coerces_bad_enum():
    data = {"type": "nope", "category": "nope", "status": "nope", "title": "x"}
    note = data_to_note(data, "en")
    assert note.type == "idea"        # fallback
    assert note.category == "misc"    # fallback
    assert note.status == "raw"       # fallback
    assert note.priority == "backlog"


def test_build_prompt_includes_category_descriptions():
    p = build_prompt(
        "some idea",
        "en",
        categories={"art": ["style", "none"], "misc": ["none"]},
        descriptions={"art": "Visual style and concepts."},
    )
    assert "- art (style, none) - Visual style and concepts." in p
    assert "- misc (none)" in p


def test_build_prompt_renders_without_descriptions_when_missing():
    p = build_prompt("some idea", "pl", categories={"art": ["style"]})
    assert "- art (style)" in p
