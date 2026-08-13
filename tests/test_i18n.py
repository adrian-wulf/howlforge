
from howlforge import vocabulary
from howlforge.i18n import CATEGORY_DESCRIPTIONS, category_description


def test_every_builtin_category_has_en_and_pl_description():
    missing = []
    for cat in vocabulary.CATEGORIES:
        for lang in ("en", "pl"):
            if not category_description(cat, lang):
                missing.append(f"{cat}:{lang}")
    assert not missing, f"Categories missing descriptions: {missing}"


def test_unknown_category_description_is_empty():
    assert category_description("does-not-exist", "en") == ""
    assert category_description("does-not-exist", "pl") == ""


def test_unknown_language_falls_back_to_english():
    assert category_description("art", "de") == CATEGORY_DESCRIPTIONS["art"]["en"]
