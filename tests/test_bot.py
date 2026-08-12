from types import SimpleNamespace

from howlforge.bot import _allowed_ids, _category_menu, _is_allowed, _menu
from howlforge.config import Settings


def _msg(chat_id, user_id):
    return SimpleNamespace(chat=SimpleNamespace(id=chat_id), from_user=SimpleNamespace(id=user_id))


def test_allowed_ids_empty_means_open():
    s = Settings(telegram_chat_id="", telegram_chat_ids="")
    assert _allowed_ids(s) == set()


def test_allowed_ids_single_and_multiple():
    s = Settings(telegram_chat_id="111", telegram_chat_ids="222, 333")
    assert _allowed_ids(s) == {"111", "222", "333"}


def test_is_allowed_open_when_empty():
    s = Settings()
    assert _is_allowed(_msg(1, 1), s) is True


def test_is_allowed_chat_id_match():
    s = Settings(telegram_chat_id="111")
    assert _is_allowed(_msg(111, 999), s) is True


def test_is_allowed_user_id_match():
    s = Settings(telegram_chat_ids="999")
    assert _is_allowed(_msg(123, 999), s) is True


def test_is_allowed_denies_stranger():
    s = Settings(telegram_chat_id="111")
    assert _is_allowed(_msg(222, 333), s) is False


def test_menu_has_buttons():
    kb = _menu("pl")
    texts = [b.text for row in kb.keyboard for b in row]
    assert "Dodaj pomysł" in texts
    assert "Nowa kategoria" in texts


def test_category_menu_has_auto_and_cancel():
    kb = _category_menu(["art", "gameplay", "story"], "en")
    texts = [b.text for row in kb.keyboard for b in row]
    assert "art" in texts
    assert "Auto (AI)" in texts
    assert "Cancel" in texts
