from howlforge import bot_state


def test_set_and_get_user(tmp_path):
    bot_state.set_user(tmp_path, 123, lang="en", project="wolfpack")
    user = bot_state.get_user(tmp_path, 123)
    assert user["lang"] == "en"
    assert user["project"] == "wolfpack"


def test_persists_across_reload(tmp_path):
    bot_state.set_user(tmp_path, 123, lang="en", project="wolfpack")
    # fresh read simulates a restart
    assert bot_state.lang_of(tmp_path, 123, "pl") == "en"
    assert bot_state.project_of(tmp_path, 123) == "wolfpack"


def test_defaults_when_unset(tmp_path):
    assert bot_state.lang_of(tmp_path, 999, "pl") == "pl"
    assert bot_state.project_of(tmp_path, 999) is None


def test_overwrite_field(tmp_path):
    bot_state.set_user(tmp_path, 123, lang="en", project="wolfpack")
    bot_state.set_user(tmp_path, 123, lang="pl")
    assert bot_state.lang_of(tmp_path, 123, "en") == "pl"
    assert bot_state.project_of(tmp_path, 123) == "wolfpack"
