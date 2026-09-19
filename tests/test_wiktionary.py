"""Парсер Wiktionary на настоящих ответах REST API."""
from anki_dict.models import BaseRef, Entry
from anki_dict.sources import wiktionary


def test_regular_word(wiktionary_json):
    entry = wiktionary.parse(wiktionary_json("concurrency.200"), "concurrency")
    assert isinstance(entry, Entry)
    assert entry.pos == "noun"
    assert entry.definition.startswith("The property or an instance of being concurrent")
    assert "<" not in entry.definition          # HTML-разметка снята
    assert entry.sound_url is None and entry.ipa == ""
    assert entry.source == "wiktionary"


def test_examples_from_real_answer(wiktionary_json):
    # у `concurrency` и `squealer` примеров в ответе нет вовсе — поле examples проверяется на `bail`
    entry = wiktionary.parse(wiktionary_json("bail.200"), "bail")
    assert entry.pos == "noun"
    assert entry.examples[0] == "He was granted bail for £20000."
    assert all("<" not in e for e in entry.examples)
    assert len(entry.examples) == len(set(entry.examples))


def test_word_without_examples(wiktionary_json):
    entry = wiktionary.parse(wiktionary_json("squealer.200"), "squealer")
    assert (entry.definition, entry.examples) == ("Any animal or person who squeals.", [])


def test_form_of_points_to_base_word(wiktionary_json):
    assert wiktionary.parse(wiktionary_json("misspoke.200"), "misspoke") == BaseRef("misspeak")


def test_no_english_section():
    payload = {"fr": [{"partOfSpeech": "Noun", "definitions": [{"definition": "chat"}]}]}
    assert wiktionary.parse(payload, "chat") is None


def test_empty_definitions_are_skipped():
    payload = {"en": [{"partOfSpeech": "Verb", "definitions": [
        {"definition": ""},
        {"definition": "To <b>do</b> it.", "examples": ["<i>Do</i> it now."]},
    ]}]}
    entry = wiktionary.parse(payload, "do")
    assert (entry.pos, entry.definition, entry.examples) == ("verb", "To do it.", ["Do it now."])


class _Resp:
    def __init__(self, status_code, payload=None):
        self.status_code, self._payload, self.url = status_code, payload, "https://en.wiktionary.org/x"

    def json(self):
        return self._payload


def test_lookup_404(monkeypatch, wiktionary_json):
    # тело 404 настоящее — убедиться, что до разбора оно не доходит
    monkeypatch.setattr(wiktionary.http, "get", lambda url, **kw: _Resp(404, wiktionary_json("ignight.404")))
    assert wiktionary.lookup("ignight") is None


def test_lookup_url_encoding(monkeypatch, wiktionary_json):
    seen = []
    monkeypatch.setattr(wiktionary.http, "get",
                        lambda url, **kw: seen.append(url) or _Resp(200, wiktionary_json("concurrency.200")))
    wiktionary.lookup("data discovery")
    wiktionary.lookup("either/or")
    assert seen[0].endswith("/definition/data_discovery")
    assert seen[1].endswith("/definition/either%2For")    # слэш — часть слова, а не путь


def test_lookup_block_is_not_not_found(monkeypatch):
    import pytest
    import requests

    monkeypatch.setattr(wiktionary.http, "get", lambda url, **kw: _Resp(403))
    with pytest.raises(requests.HTTPError):
        wiktionary.lookup("cat")
