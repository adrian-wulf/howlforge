import pytest
from fastapi.testclient import TestClient

from howlforge.config import Settings
from howlforge.schema import Note
from howlforge.vault import write_note


@pytest.fixture
def client(tmp_path, monkeypatch):
    settings = Settings(language="en", vault_path=tmp_path, llm_model="howl-classify")
    monkeypatch.setattr("howlforge.server.get_settings", lambda: settings)
    from howlforge import server

    return TestClient(server.app)


def _seed(vault, *notes):
    for n in notes:
        write_note(n, vault)


def test_api_notes_empty(client):
    r = client.get("/api/notes")
    assert r.status_code == 200
    assert r.json() == []


def test_api_notes_lists_and_filters(client, tmp_path):
    _seed(
        tmp_path,
        Note(title="Wolf A", status="raw", project="wolfpack", category="gameplay"),
        Note(title="Wolf B", status="processed", project="wolfpack", category="gameplay"),
        Note(title="Farm C", status="raw", project="cowboy-farm", category="mechanics"),
    )
    all_rows = client.get("/api/notes").json()
    assert len(all_rows) == 3

    raw = client.get("/api/notes", params={"status": "raw"}).json()
    assert {r["title"] for r in raw} == {"Wolf A", "Farm C"}

    proj = client.get("/api/notes", params={"project": "wolfpack"}).json()
    assert {r["title"] for r in proj} == {"Wolf A", "Wolf B"}


def test_api_patch_updates_status(client, tmp_path):
    note = Note(title="Wolf A", status="raw", project="wolfpack")
    write_note(note, tmp_path)
    path = "00 Inbox/wolf-a.md"
    r = client.patch(f"/api/notes/{path}", json={"status": "implemented"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    # confirm persisted
    back = (tmp_path / path).read_text(encoding="utf-8")
    assert "status: implemented" in back


def test_api_patch_invalid_status_422(client, tmp_path):
    note = Note(title="Wolf A", status="raw")
    write_note(note, tmp_path)
    path = "00 Inbox/wolf-a.md"
    r = client.patch(f"/api/notes/{path}", json={"status": "shipped"})
    assert r.status_code == 422


def test_api_patch_missing_404(client):
    r = client.patch("/api/notes/nope.md", json={"status": "raw"})
    assert r.status_code == 404


def test_api_patch_path_escape_422(client, tmp_path):
    write_note(Note(title="Wolf A", status="raw"), tmp_path)
    r = client.patch("/api/notes/../secret.md", json={"status": "raw"})
    assert r.status_code in (404, 422)


def test_panel_renders(client, tmp_path):
    write_note(Note(title="Wolf A", status="raw", project="wolfpack"), tmp_path)
    r = client.get("/panel")
    assert r.status_code == 200
    assert "HowlForge" in r.text
