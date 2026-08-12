from howlforge import i18n, vocabulary


def test_statuses_valid():
    assert vocabulary.is_valid_status("raw")
    assert vocabulary.is_valid_status("implemented")
    assert not vocabulary.is_valid_status("shipped")


def test_priority_valid():
    assert vocabulary.is_valid_priority("high")
    assert not vocabulary.is_valid_priority("urgent")


def test_category_subcategory_pairs():
    assert vocabulary.is_valid_category("art")
    assert vocabulary.is_valid_subcategory("art", "style")
    assert not vocabulary.is_valid_subcategory("art", "plot")  # plot belongs to story
    assert vocabulary.is_valid_subcategory("story", "plot")


def test_type_valid():
    assert vocabulary.is_valid_type("idea")
    assert vocabulary.is_valid_type("gdd")
    assert not vocabulary.is_valid_type("random")


def test_destination_mapping():
    assert vocabulary.destination_for("idea") == "00 Inbox"
    assert vocabulary.destination_for("gdd") == "10 Projects/{project}/GDD"
    assert vocabulary.destination_for("system") == "20 Systems"


def test_i18n_pl_labels():
    assert i18n.status_label("raw", "pl") == "Surowe"
    assert i18n.priority_label("high", "pl") == "Wysoki"
    assert i18n.category_label("story", "pl") == "Fabuła"


def test_i18n_en_fallback():
    assert i18n.status_label("raw", "en") == "Raw"
    assert i18n.status_label("raw", "xx") == "Raw"  # unknown lang -> default
    assert i18n.type_label("idea", "pl") == "Pomysł"
