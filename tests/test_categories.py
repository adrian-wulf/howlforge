import pytest

from howlforge import categories as categories_mod
from howlforge.capture import capture_manual
from howlforge.config import Settings


def test_add_and_load(tmp_path):
    categories_mod.add(tmp_path, "Narrative Design", ["Plot", "Dialogue"])
    custom = categories_mod.load(tmp_path)
    assert custom == {"narrative-design": ["plot", "dialogue"]}


def test_duplicate_builtin_raises(tmp_path):
    with pytest.raises(ValueError):
        categories_mod.add(tmp_path, "Art")


def test_duplicate_custom_raises(tmp_path):
    categories_mod.add(tmp_path, "Narrative")
    with pytest.raises(ValueError):
        categories_mod.add(tmp_path, "Narrative")


def test_empty_name_raises(tmp_path):
    with pytest.raises(ValueError):
        categories_mod.add(tmp_path, "  ")


def test_all_categories_merges(tmp_path):
    categories_mod.add(tmp_path, "Narrative")
    cats = categories_mod.all_categories(tmp_path)
    assert "art" in cats
    assert "narrative" in cats


def test_capture_manual_with_custom_category(tmp_path):
    categories_mod.add(tmp_path, "Narrative", ["Plot"])
    settings = Settings(language="pl", vault_path=tmp_path)
    result = capture_manual(
        "A branching plot idea",
        settings,
        category="narrative",
        subcategory="plot",
    )
    assert result.ok
    assert result.note.category == "narrative"


def test_capture_manual_custom_unknown_subcategory_raises(tmp_path):
    categories_mod.add(tmp_path, "Narrative", ["Plot"])
    settings = Settings(language="pl", vault_path=tmp_path)
    with pytest.raises(Exception):
        capture_manual("x", settings, category="narrative", subcategory="music")


def test_capture_manual_builtin_unknown_raises(tmp_path):
    settings = Settings(language="pl", vault_path=tmp_path)
    with pytest.raises(Exception):
        capture_manual("x", settings, category="nope")


def test_remove_category(tmp_path):
    categories_mod.add(tmp_path, "Narrative", ["Plot"])
    assert categories_mod.remove(tmp_path, "Narrative") is True
    assert "narrative" not in categories_mod.load(tmp_path)


def test_remove_missing_returns_false(tmp_path):
    assert categories_mod.remove(tmp_path, "nonexistent") is False


def test_remove_builtin_raises(tmp_path):
    with pytest.raises(ValueError):
        categories_mod.remove(tmp_path, "Art")


def test_add_with_description_round_trip(tmp_path):
    categories_mod.add(tmp_path, "Books", ["Fiction"], description="Books to read and review.")
    assert categories_mod.load(tmp_path) == {"books": ["fiction"]}
    assert categories_mod.load_descriptions(tmp_path) == {"books": "Books to read and review."}


def test_legacy_list_format_still_loads(tmp_path):
    p = tmp_path / ".howlforge" / "categories.json"
    p.parent.mkdir(parents=True)
    p.write_text('{"old-cat": ["a", "b"]}', encoding="utf-8")
    assert categories_mod.load(tmp_path) == {"old-cat": ["a", "b"]}
    assert categories_mod.load_descriptions(tmp_path) == {}


def test_merged_descriptions_include_builtins_and_custom(tmp_path):
    categories_mod.add(tmp_path, "Books", description="Books to read.")
    merged_en = categories_mod.merged_descriptions(tmp_path, "en")
    assert merged_en["art"].startswith("Visual style")
    assert merged_en["books"] == "Books to read."
    merged_pl = categories_mod.merged_descriptions(tmp_path, "pl")
    assert merged_pl["art"].startswith("Styl wizualny")
    assert merged_pl["books"] == "Books to read."


def test_add_whitespace_description_ignored(tmp_path):
    categories_mod.add(tmp_path, "Books", description="   ")
    assert categories_mod.load_descriptions(tmp_path) == {}
    assert categories_mod.load(tmp_path) == {"books": ["none"]}


def test_load_descriptions_tolerates_malformed_file(tmp_path):
    p = tmp_path / ".howlforge" / "categories.json"
    p.parent.mkdir(parents=True)
    p.write_text("{not json", encoding="utf-8")
    assert categories_mod.load_descriptions(tmp_path) == {}
    assert categories_mod.load(tmp_path) == {}


def test_load_descriptions_ignores_non_dict_entries(tmp_path):
    p = tmp_path / ".howlforge" / "categories.json"
    p.parent.mkdir(parents=True)
    payload = '{"plain": ["a"], "obj": {"subcategories": ["b"], "description": "D"}}'
    p.write_text(payload, encoding="utf-8")
    assert categories_mod.load_descriptions(tmp_path) == {"obj": "D"}
    assert categories_mod.load(tmp_path) == {"plain": ["a"], "obj": ["b"]}


def test_add_with_description_keeps_existing_categories(tmp_path):
    categories_mod.add(tmp_path, "First")
    categories_mod.add(tmp_path, "Second", description="Second desc")
    custom = categories_mod.load(tmp_path)
    assert custom == {"first": ["none"], "second": ["none"]}
    assert categories_mod.load_descriptions(tmp_path) == {"second": "Second desc"}
