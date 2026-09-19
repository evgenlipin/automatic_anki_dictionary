"""Парсер Cambridge на настоящих страницах — по одной на каждый вид статьи."""
import pytest
import requests

from anki_dict.models import BaseRef, Entry
from anki_dict.sources import cambridge


def parse(cambridge_html, slug):
    return cambridge.parse(cambridge_html(slug), slug.replace("-", " "))


def test_regular_word(cambridge_html):
    entry = parse(cambridge_html, "superficial")
    assert isinstance(entry, Entry)
    assert entry.pos == "adjective"
    assert entry.definition.startswith("(of a person) never thinking about things that are serious")
    assert entry.ipa == "ˌsuː.pəˈfɪʃ.əl"
    assert entry.examples[0] == "He's fun to be with, but he's very superficial."
    assert len(entry.examples) >= 3
    assert entry.sound_url.startswith("https://dictionary.cambridge.org/media/") and entry.sound_url.endswith(".mp3")
    assert entry.source == "cambridge"


def test_examples_are_unique(cambridge_html):
    # второй круг идёт по всей странице и заново встречает примеры первого блока
    examples = parse(cambridge_html, "superficial").examples
    assert len(examples) == len(set(examples))


def test_phrasal_verb(cambridge_html):
    entry = parse(cambridge_html, "come-over")
    assert entry.pos == "phrasal verb"
    # хвостовой пробел — как на сайте и как в уже импортированных карточках (от него зависит guid)
    assert entry.definition == "to seem to be a particular type of person: "
    assert "I watched the interview and felt he came over as quite arrogant." in entry.examples


def test_idiom_block_inside_another_entry(cambridge_html):
    # `facilities` ведётся фразой внутри статьи `facility`: обычного контейнера статьи на странице нет
    entry = parse(cambridge_html, "facilities")
    assert isinstance(entry, Entry)
    assert entry.definition.startswith("the buildings, equipment, and services")
    assert len(entry.examples) >= 3
    assert (entry.pos, entry.ipa, entry.sound_url) == ("phrase", "", None)


def test_idiom_without_pos_tag(cambridge_html):
    entry = parse(cambridge_html, "in-the-trenches")
    assert entry.pos == "idiom"
    assert entry.definition.startswith("working in the most active and difficult parts")
    assert entry.ipa == ""


def test_inflected_form_points_to_base_word(cambridge_html):
    assert parse(cambridge_html, "bailed") == BaseRef("bail")


def test_entry_without_sound(cambridge_html):
    entry = parse(cambridge_html, "head-out")
    assert isinstance(entry, Entry)
    # на странице бывает виджет «Word of the Day» со своим mp3 (есть не при каждой загрузке):
    # звук ищется только внутри статьи, иначе карточка получает произношение чужого слова
    assert entry.sound_url is None
    assert len(entry.examples) == 2   # меньше трёх → pipeline добирает через LLM


def test_single_example_on_whole_page(cambridge_html):
    assert len(parse(cambridge_html, "womb").examples) == 1


def test_unknown_word_redirects_to_home_page(cambridge_html):
    assert parse(cambridge_html, "ignight") is None


def test_corpus_only_page_is_not_an_entry(cambridge_html):
    # у `concurrency` статьи нет — только страница «Examples of …» из корпуса
    assert parse(cambridge_html, "concurrency") is None


class _Resp:
    def __init__(self, status_code, text="", url="https://dictionary.cambridge.org/x"):
        self.status_code, self.text, self.url = status_code, text, url


def test_lookup_uses_dashed_slug(monkeypatch, cambridge_html):
    seen = []
    monkeypatch.setattr(cambridge.http, "get", lambda url, **kw: seen.append(url) or _Resp(200, cambridge_html("come-over")))
    assert cambridge.lookup("come over").pos == "phrasal verb"
    assert seen == ["https://dictionary.cambridge.org/dictionary/english/come-over"]


def test_lookup_404_means_not_found(monkeypatch):
    monkeypatch.setattr(cambridge.http, "get", lambda url, **kw: _Resp(404))
    assert cambridge.lookup("zzz") is None


@pytest.mark.parametrize("status", [403, 429, 500, 503])
def test_lookup_block_or_server_error_is_not_not_found(monkeypatch, status):
    # сбой или бан — не «слова нет»: строка должна остаться в words.txt. Иначе при заблокированном
    # Cambridge все слова молча ушли бы в Wiktionary и получились без звука
    monkeypatch.setattr(cambridge.http, "get", lambda url, **kw: _Resp(status))
    with pytest.raises(requests.HTTPError):
        cambridge.lookup("cat")


def test_slug():
    assert cambridge.slug("come over") == "come-over"
    assert cambridge.slug("well-being") == "well-being"
    assert cambridge.slug("devil's advocate") == "devil-s-advocate"
