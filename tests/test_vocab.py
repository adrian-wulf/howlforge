from howlforge import vocab as vocab_mod


def test_builtin_statuses_and_priorities():
    statuses = vocab_mod.all_statuses()
    priorities = vocab_mod.all_priorities()
    assert [s["key"] for s in statuses] == [
        "raw", "processed", "prototype", "implemented", "rejected", "archived",
    ]
    assert "critical" in [p["key"] for p in priorities]
    # built-ins have labels + colors
    assert statuses[0]["label_en"]
    assert statuses[0]["color"]


def test_add_and_list_custom_status(tmp_path):
    vocab_mod.add_status(tmp_path, "shipped", "Shipped", "Wydane", "#112233")
    statuses = vocab_mod.all_statuses(tmp_path)
    keys = [s["key"] for s in statuses]
    assert "shipped" in keys
    shipped = next(s for s in statuses if s["key"] == "shipped")
    assert shipped["label_pl"] == "Wydane"
    assert shipped["color"] == "#112233"


def test_add_priority(tmp_path):
    vocab_mod.add_priority(tmp_path, "urgent", "Urgent", "Pilny", "#ff0000")
    assert "urgent" in vocab_mod.priority_keys(tmp_path)


def test_add_builtin_status_raises(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        vocab_mod.add_status(tmp_path, "raw")


def test_remove_custom_status(tmp_path):
    vocab_mod.add_status(tmp_path, "shipped")
    assert vocab_mod.remove(tmp_path, "statuses", "shipped") is True
    assert "shipped" not in vocab_mod.status_keys(tmp_path)


def test_remove_builtin_raises(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        vocab_mod.remove(tmp_path, "statuses", "raw")
