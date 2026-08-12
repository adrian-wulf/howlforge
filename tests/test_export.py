import csv
import io
import json

from howlforge.export import export_file, generate
from howlforge.schema import Note
from howlforge.vault import write_note


def _seed(tmp_path):
    write_note(
        Note(title="Wolf pack", project="wolfpack", category="gameplay", tags=["coop"]),
        tmp_path,
    )
    write_note(
        Note(title="Crop pricing", project="cowboy-farm", category="mechanics", tags=["economy"]),
        tmp_path,
    )


def test_generate_json(tmp_path):
    _seed(tmp_path)
    payload = generate(tmp_path, "json")
    data = json.loads(payload)
    assert len(data) == 2
    assert {r["title"] for r in data} == {"Wolf pack", "Crop pricing"}
    assert "tags" in data[0]


def test_generate_json_filter_project(tmp_path):
    _seed(tmp_path)
    data = json.loads(generate(tmp_path, "json", project="wolfpack"))
    assert len(data) == 1
    assert data[0]["title"] == "Wolf pack"


def test_generate_csv(tmp_path):
    _seed(tmp_path)
    rows = list(csv.DictReader(io.StringIO(generate(tmp_path, "csv"))))
    assert len(rows) == 2
    assert {"Wolf pack", "Crop pricing"} == {r["title"] for r in rows}
    assert all("tags" not in r for r in rows)  # scalar columns only


def test_generate_unknown_format_raises(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        generate(tmp_path, "xml")


def test_export_file(tmp_path):
    _seed(tmp_path)
    out = tmp_path / "export.json"
    export_file(tmp_path, out)
    assert out.exists()
    assert len(json.loads(out.read_text(encoding="utf-8"))) == 2
