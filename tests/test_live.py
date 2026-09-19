"""Живой смоук: настоящая сеть, без картинок. Детектор смены вёрстки Cambridge и формата Wiktionary.

    docker compose run --rm test -m live

Три класса слов: предметное, абстрактное, фразовый глагол — плюс слово, которое есть только в Wiktionary.
"""
import time

import pytest

from anki_dict.models import Entry
from anki_dict.sources import cambridge, wiktionary

pytestmark = pytest.mark.live


@pytest.fixture(autouse=True)
def _pause():
    yield
    time.sleep(2)   # не долбить словари


@pytest.mark.parametrize("word,pos", [("bureaucracy", "noun"), ("superficial", "adjective"), ("come over", "phrasal verb")])
def test_cambridge_entry(word, pos):
    entry = cambridge.lookup(word)
    assert isinstance(entry, Entry)
    assert entry.pos == pos
    assert entry.definition and entry.examples
    assert entry.sound_url and entry.sound_url.endswith(".mp3")


def test_cambridge_unknown_word():
    assert cambridge.lookup("ignight") is None


def test_wiktionary_entry():
    entry = wiktionary.lookup("concurrency")
    assert isinstance(entry, Entry) and entry.pos == "noun" and entry.definition
