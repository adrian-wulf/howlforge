import pytest
from fastapi.testclient import TestClient

from howlforge.config import Settings
from howlforge.schema import Note
from howlforge.vault import write_note


@pytest.fixture
def client(tmp_path, monkeypatch):
    settings = Settings(
        language="en", vault_path=tmp_path, llm_model="howl-classify",
        panel_password="super-secret",
    )
    monkeypatch.setattr("howlforge.server.get_settings", lambda: settings)
    from howlforge import server

    return TestClient(server.app)


def test_panel_redirects_to_login_without_cookie(client, tmp_path):
    write_note(Note(title="Wolf A"), tmp_path)
    r = client.get("/panel", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


def test_api_unauthorized_401_without_cookie(client):
    r = client.get("/api/notes")
    assert r.status_code == 401


def test_login_wrong_password(client):
    r = client.post("/login", data={"password": "nope"})
    assert r.status_code == 200
    assert "Błędne hasło" in r.text or "Wrong password" in r.text


def test_login_correct_password_sets_cookie(client):
    r = client.post("/login", data={"password": "super-secret"}, follow_redirects=False)
    assert r.status_code == 303
    assert "howlforge_auth" in r.headers.get("set-cookie", "")


def test_panel_accessible_with_cookie(client, tmp_path):
    write_note(Note(title="Wolf A"), tmp_path)
    client.post("/login", data={"password": "super-secret"})
    r = client.get("/panel")
    assert r.status_code == 200
    assert "Wolf A" in r.text


def test_api_accessible_with_cookie(client):
    client.post("/login", data={"password": "super-secret"})
    r = client.get("/api/notes")
    assert r.status_code == 200
