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


def test_capture_manual_no_ai(client, tmp_path):
    r = client.post(
        "/api/capture",
        json={"text": "A brand new idea", "ai": False, "project": "wolfpack",
              "category": "gameplay", "priority": "high", "status": "raw"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["title"] == "A brand new idea"
    # file exists and has the project
    saved = tmp_path / "00 Inbox" / "a-brand-new-idea.md"
    assert saved.exists()
    assert "project: wolfpack" in saved.read_text(encoding="utf-8")


def test_capture_manual_empty_422(client):
    r = client.post("/api/capture", json={"text": "   ", "ai": False})
    assert r.status_code == 422


def test_projects_list_and_create(client, tmp_path):
    assert client.get("/api/projects").json() == []
    r = client.post("/api/projects", json={"name": "Cowboy Farm"})
    assert r.status_code == 200
    assert r.json() == {"name": "Cowboy Farm", "slug": "cowboy-farm"}
    assert client.get("/api/projects").json() == ["cowboy-farm"]
    assert (tmp_path / "10 Projects" / "cowboy-farm").is_dir()


def test_api_categories_create_and_list(client, tmp_path):
    r = client.post(
        "/api/categories", json={"name": "Narrative", "subcategories": ["Plot", "Dialogue"]}
    )
    assert r.status_code == 200
    assert r.json()["slug"] == "narrative"
    cats = client.get("/api/categories").json()
    assert "art" in cats
    assert cats["narrative"] == ["plot", "dialogue"]


def test_api_categories_duplicate_422(client):
    r = client.post("/api/categories", json={"name": "Art"})
    assert r.status_code == 422


def test_api_delete_note(client, tmp_path):
    write_note(Note(title="Wolf A", status="raw"), tmp_path)
    r = client.delete("/api/notes/00%20Inbox/wolf-a.md")
    assert r.status_code == 200
    assert not (tmp_path / "00 Inbox" / "wolf-a.md").exists()
    # second delete -> 404
    assert client.delete("/api/notes/00%20Inbox/wolf-a.md").status_code == 404


def test_api_delete_project(client, tmp_path):
    write_note(Note(title="Wolf A", type="mechanic", project="wolfpack"), tmp_path)
    r = client.delete("/api/projects/wolfpack")
    assert r.status_code == 200
    assert r.json()["notes_deleted"] == 1
    assert not (tmp_path / "10 Projects" / "wolfpack").exists()


def test_api_delete_category(client, tmp_path):
    client.post("/api/categories", json={"name": "Narrative"})
    r = client.delete("/api/categories/narrative")
    assert r.status_code == 200
    assert "narrative" not in client.get("/api/categories").json()


def test_api_vocab_and_add_status(client, tmp_path):
    v = client.get("/api/vocab").json()
    assert "statuses" in v and "priorities" in v
    r = client.post(
        "/api/statuses", json={"key": "Shipped", "label_en": "Shipped", "label_pl": "Wydane"}
    )
    assert r.status_code == 200
    assert r.json()["key"] == "shipped"
    keys = [s["key"] for s in client.get("/api/vocab").json()["statuses"]]
    assert "shipped" in keys


def test_api_delete_status(client, tmp_path):
    client.post("/api/statuses", json={"key": "shipped"})
    assert client.delete("/api/statuses/shipped").status_code == 200
    assert client.delete("/api/statuses/shipped").status_code == 404


def test_panel_board_renders(client, tmp_path):
    write_note(Note(title="Wolf A", status="raw", project="wolfpack"), tmp_path)
    r = client.get("/panel/project/wolfpack/board")
    assert r.status_code == 200
    assert "Wolf A" in r.text
    assert "Tablica" in r.text or "Board" in r.text


def test_patch_project_moves_note(client, tmp_path):
    # a "mechanic" without a project sits in the generic Mechanics folder
    write_note(Note(title="Wolf A", status="raw", type="mechanic"), tmp_path)
    old_path = "10 Projects/Mechanics/wolf-a.md"
    r = client.patch(f"/api/notes/{old_path}", json={"project": "wolfpack"})
    assert r.status_code == 200
    new = tmp_path / "10 Projects" / "wolfpack" / "Mechanics" / "wolf-a.md"
    assert new.exists()
    assert "project: wolfpack" in new.read_text(encoding="utf-8")


def test_api_get_note_full(client, tmp_path):
    write_note(Note(title="Wolf A", status="raw", body="The body text"), tmp_path)
    r = client.get("/api/notes/00%20Inbox/wolf-a.md")
    assert r.status_code == 200
    d = r.json()
    assert d["title"] == "Wolf A"
    assert d["body"] == "The body text"


def test_api_get_note_missing_404(client):
    assert client.get("/api/notes/nope.md").status_code == 404


def test_panel_note_editor(client, tmp_path):
    write_note(Note(title="Wolf A", status="raw", body="Body here"), tmp_path)
    r = client.get("/panel/note/00%20Inbox/wolf-a.md")
    assert r.status_code == 200
    assert "Body here" in r.text
    assert 'name="title"' in r.text


def test_panel_project_dashboard(client, tmp_path):
    write_note(Note(title="Wolf A", status="raw", project="wolfpack"), tmp_path)
    write_note(Note(title="Wolf B", status="processed", project="wolfpack"), tmp_path)
    r = client.get("/panel/project/wolfpack")
    assert r.status_code == 200
    assert "Wolf A" in r.text
    assert "Wolf B" in r.text
    assert "2" in r.text  # total notes


def test_api_category_create_with_description(client, tmp_path):
    r = client.post(
        "/api/categories",
        json={"name": "Books", "subcategories": ["Fiction"], "description": "Books to read."},
    )
    assert r.status_code == 200
    assert r.json()["description"] == "Books to read."
    from howlforge import categories as categories_mod

    assert categories_mod.load_descriptions(tmp_path) == {"books": "Books to read."}
