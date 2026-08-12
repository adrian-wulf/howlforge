import pytest

from howlforge.schema import Note
from howlforge.vault import destination_path, update_note, write_note


def test_note_defaults_roundtrip():
    n = Note(title="My First Idea", body="Some body text.", language="pl")
    md = n.to_markdown()
    assert md.startswith("---\n")
    back = Note.from_markdown(md)
    assert back.title == "My First Idea"
    assert back.body == "Some body text."
    assert back.language == "pl"


def test_note_valid():
    n = Note(title="Ok", category="art", subcategory="style", status="raw")
    assert n.is_valid
    assert n.validate() == []


def test_note_invalid_category():
    n = Note(title="Bad", category="nope")
    assert not n.is_valid
    assert any("category" in e for e in n.validate())


def test_note_invalid_subcategory():
    n = Note(title="Bad pair", category="story", subcategory="style")  # style is art
    assert not n.is_valid


def test_destination_with_project():
    n = Note(type="gdd", project="cowboy-farm", title="GDD")
    assert "10 Projects/cowboy-farm/GDD" in str(destination_path(n, "vault"))


def test_write_note_creates_file(tmp_path):
    n = Note(title="An Idea", category="mechanics", subcategory="economy", body="text")
    path = write_note(n, tmp_path)
    assert path.exists()
    assert path.suffix == ".md"


def test_write_note_never_overwrites(tmp_path):
    a = Note(title="Same", body="one")
    b = Note(title="Same", body="two")
    p1 = write_note(a, tmp_path)
    p2 = write_note(b, tmp_path)
    assert p1 != p2
    assert p2.name.endswith("-2.md")


def test_update_note_changes_status_and_priority(tmp_path):
    path = write_note(Note(title="Wolf", status="raw", priority="low"), tmp_path)
    rel = path.relative_to(tmp_path)
    updated = update_note(tmp_path, str(rel), status="processed", priority="high")
    assert updated.status == "processed"
    assert updated.priority == "high"
    assert "status: processed" in path.read_text(encoding="utf-8")


def test_update_note_rejects_invalid_status(tmp_path):
    path = write_note(Note(title="Wolf", status="raw"), tmp_path)
    rel = path.relative_to(tmp_path)
    with pytest.raises(ValueError):
        update_note(tmp_path, str(rel), status="shipped")

