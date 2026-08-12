import pytest

from howlforge.schema import Note
from howlforge.search import SearchError, index_vault, search
from howlforge.vault import write_note

_VOCAB = ["wolf", "pack", "coop", "crop", "price", "farming", "economy", "night"]


class FakeEmbedder:
    available_models = ["howl-embed"]

    def embed(self, text: str, model=None):
        words = text.lower().split()
        return [float(words.count(w)) for w in _VOCAB]


def _seed(tmp_path):
    write_note(
        Note(title="Wolf pack", category="gameplay", body="coop wolves"),
        tmp_path,
    )
    write_note(
        Note(title="Crop pricing", category="mechanics", body="economy prices"),
        tmp_path,
    )


def test_index_vault_counts(tmp_path):
    _seed(tmp_path)
    client = FakeEmbedder()
    assert index_vault(tmp_path, client) == 2


def test_search_ranks_similar_higher(tmp_path):
    _seed(tmp_path)
    client = FakeEmbedder()
    index_vault(tmp_path, client)
    hits = search(tmp_path, client, "wolf pack coop", k=5)
    assert hits
    assert hits[0].title == "Wolf pack"
    assert hits[0].score >= 0
    # descending
    assert all(hits[i].score >= hits[i + 1].score for i in range(len(hits) - 1))


def test_search_empty_index_raises(tmp_path):
    client = FakeEmbedder()
    with pytest.raises(SearchError):
        search(tmp_path, client, "anything", k=5)


def test_search_empty_query_raises(tmp_path):
    _seed(tmp_path)
    client = FakeEmbedder()
    index_vault(tmp_path, client)
    with pytest.raises(SearchError):
        search(tmp_path, client, "   ", k=5)


def test_index_is_excluded_from_note_listing(tmp_path):
    from howlforge.vault import list_notes

    _seed(tmp_path)
    index_vault(tmp_path, FakeEmbedder())
    paths = [str(p.relative_to(tmp_path)) for p in list_notes(tmp_path)]
    assert not any(".howlforge" in p for p in paths)
    assert len(paths) == 2
