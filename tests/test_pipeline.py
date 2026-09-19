"""Путь слова и прогон words.txt — с подставными словарями, LLM и картинками, без сети."""
from pathlib import Path

import pytest
import requests

from anki_dict import deck, pipeline as pipeline_module
from anki_dict.inspect_apkg import broken_refs, read_apkg
from anki_dict.models import BaseRef, Card, Entry, NotFound, media_name
from anki_dict.pipeline import Pipeline, run_batch
from anki_dict.wordlist import parse_line


def entry(word, examples=(), sound=True, source="cambridge"):
    return Entry(word=word, pos="noun", definition=f"meaning of {word}:", ipa="ipa",
                 examples=list(examples), sound_url="https://x/s.mp3" if sound else None, source=source)


def make_pipeline(cambridge=None, wiktionary=None, generated=(), spelling=None, collage=False, calls=None):
    calls = calls if calls is not None else []

    def lookup(name, table):
        def inner(word):
            calls.append((name, word))
            found = (table or {}).get(word)
            if isinstance(found, Exception):
                raise found
            return found
        return inner

    def make_collage(media_dir, word, definition, example):
        path = Path(media_dir) / f"collage_{media_name(word)}.jpg"
        path.write_bytes(b"jpg")
        return path

    return Pipeline(
        lookup_cambridge=lookup("cambridge", cambridge),
        lookup_wiktionary=lookup("wiktionary", wiktionary),
        generate_examples=lambda word, meaning, need: list(generated)[:need],
        suggest_spelling=lambda word: spelling,
        download=lambda url, path: Path(path).write_bytes(b"mp3"),
        make_collage=make_collage if collage else None,
    )


# ---------- одно слово ----------

def test_custom_example_goes_first_then_dictionary(tmp_path):
    p = make_pipeline(cambridge={"womb": entry("womb", ["A.", "B.", "C.", "D."])})
    card = p.process(parse_line("womb - My own sentence."), tmp_path)
    assert card.examples == ["My own sentence.", "A.", "B."]


def test_llm_tops_up_to_three_without_duplicates(tmp_path):
    # LLM повторил словарный пример «A.» — дубль отсеян, до трёх добрано следующими
    p = make_pipeline(cambridge={"womb": entry("womb", ["A."])}, generated=["A.", "G1.", "G2.", "G3."])
    p.generate_examples = lambda word, meaning, need: ["A.", "G1.", "G2.", "G3."]
    assert p.process(parse_line("womb"), tmp_path).examples == ["A.", "G1.", "G2."]


def test_fewer_than_three_when_llm_gives_too_little(tmp_path):
    p = make_pipeline(cambridge={"womb": entry("womb", ["A."])}, generated=["G1."])
    assert p.process(parse_line("womb"), tmp_path).examples == ["A.", "G1."]


def test_collage_crash_does_not_cost_the_card(tmp_path, capsys):
    p = make_pipeline(cambridge={"womb": entry("womb", ["A.", "B.", "C."])}, collage=True)
    p.make_collage = lambda *a: (_ for _ in ()).throw(RuntimeError("PIL exploded"))
    card = p.process(parse_line("womb"), tmp_path)
    assert isinstance(card, Card) and card.collage_path is None and card.sound_path is not None
    assert "коллаж не получился" in capsys.readouterr().out


def test_apostrophe_does_not_break_media_references(tmp_path):
    p = make_pipeline(cambridge={"devil's advocate": entry("devil's advocate", ["A.", "B.", "C."])}, collage=True)
    card = p.process(parse_line("devil's advocate"), tmp_path)
    assert card.sound_path.name == "devil_s_advocate.mp3"
    assert card.collage_path.name == "collage_devil_s_advocate.jpg"

    out = tmp_path / "out.apkg"
    deck.write_package([card], out, tmp_path / "backups")
    apkg = read_apkg(out)
    assert apkg["notes"][0]["fields"][0] == "devil's advocate"     # само слово не трогаем
    assert broken_refs(apkg) == []


def test_llm_failure_keeps_the_card(tmp_path):
    p = make_pipeline(cambridge={"womb": entry("womb", ["A."])})
    p.generate_examples = lambda *a: (_ for _ in ()).throw(requests.ConnectionError("down"))
    card = p.process(parse_line("womb"), tmp_path)
    assert isinstance(card, Card) and card.examples == ["A."]


def test_inflected_form_keeps_original_word_and_file_name(tmp_path):
    p = make_pipeline(cambridge={"bailed": BaseRef("bail"), "bail": entry("bail", ["A.", "B.", "C."])})
    card = p.process(parse_line("bailed"), tmp_path)
    assert card.word == "bailed"
    assert card.sound_path.name == "bailed.mp3" and card.sound_path.exists()


def test_wiktionary_is_used_when_cambridge_has_nothing(tmp_path):
    p = make_pipeline(wiktionary={"djing": entry("djing", sound=False, source="wiktionary")}, generated=["Djing a.", "Djing b.", "Djing c."])
    card = p.process(parse_line("djing"), tmp_path)
    assert (card.source, card.sound_path, len(card.examples)) == ("wiktionary", None, 3)


def test_wiktionary_form_of_returns_to_cambridge_for_sound(tmp_path):
    calls = []
    p = make_pipeline(cambridge={"misspeak": entry("misspeak", ["A.", "B.", "C."])},
                      wiktionary={"misspoke": BaseRef("misspeak")}, calls=calls)
    card = p.process(parse_line("misspoke"), tmp_path)
    assert calls == [("cambridge", "misspoke"), ("wiktionary", "misspoke"), ("cambridge", "misspeak")]
    assert (card.word, card.source) == ("misspoke", "cambridge")
    assert card.sound_path is not None


def test_base_word_loop_does_not_hang(tmp_path):
    p = make_pipeline(cambridge={"a": BaseRef("b"), "b": BaseRef("a")})
    assert isinstance(p.process(parse_line("a"), tmp_path), NotFound)


def test_typo_hint_only_if_candidate_exists(tmp_path):
    known = {"ignite": entry("ignite")}
    assert make_pipeline(cambridge=known, spelling="ignite").process(parse_line("ignight"), tmp_path) == NotFound("ignite")
    assert make_pipeline(cambridge=known, spelling="ignyte").process(parse_line("ignight"), tmp_path) == NotFound(None)
    assert make_pipeline(cambridge=known, spelling=None).process(parse_line("ignight"), tmp_path) == NotFound(None)


def test_no_hint_for_a_whole_sentence(tmp_path):
    p = make_pipeline(cambridge={"x": entry("x")}, spelling="x")
    assert p.process(parse_line("data discovery is an important prerequisite"), tmp_path) == NotFound(None)


def test_dictionary_network_error_propagates(tmp_path):
    p = make_pipeline(cambridge={"womb": requests.ConnectionError("down")})
    with pytest.raises(requests.RequestException):
        p.process(parse_line("womb"), tmp_path)


# ---------- прогон words.txt ----------

@pytest.fixture
def ws(tmp_path):
    tmp_path.joinpath("words.txt").write_text(
        "womb - My own womb sentence.\n\nignight - My typo sentence.\nflaky\n", encoding="utf-8")
    return tmp_path


def batch_pipeline(**kw):
    return make_pipeline(
        cambridge={"womb": entry("womb", ["A.", "B.", "C."]), "ignite": entry("ignite"),
                   "flaky": requests.ConnectionError("down")},
        spelling="ignite", **kw)


def lines(path):
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def test_three_outcomes(ws):
    cards = run_batch(ws, batch_pipeline(collage=True), throttle=0)

    assert [c.word for c in cards] == ["womb"]
    assert lines(ws / "success_words.txt") == ["womb - My own womb sentence."]
    # свой пример слова-неудачника не теряется, подсказка — хвостом
    assert lines(ws / "problem_words.txt") == ["ignight - My typo sentence.   # возможно: ignite"]
    # сетевой сбой — не «нет в словаре»: строка остаётся на следующий прогон
    assert lines(ws / "words.txt") == ["flaky"]

    apkg = read_apkg(ws / "output.apkg")
    assert [n["fields"][0] for n in apkg["notes"]] == ["womb"]
    assert apkg["notes"][0]["fields"][4].startswith("<br>• My own womb sentence.")
    assert apkg["media"] == {"womb.mp3", "collage_womb.jpg"}


def test_second_run_does_not_duplicate_journals(ws):
    run_batch(ws, batch_pipeline(), throttle=0)
    ws.joinpath("words.txt").write_text("womb - My own womb sentence.\nignight - My typo sentence.\n", encoding="utf-8")
    run_batch(ws, batch_pipeline(), throttle=0)
    assert len(lines(ws / "success_words.txt")) == 1
    assert len(lines(ws / "problem_words.txt")) == 1


def test_previous_deck_survives_in_backups(ws):
    ws.joinpath("output.apkg").write_bytes(b"old deck")
    run_batch(ws, batch_pipeline(), throttle=0)
    assert [p.read_bytes() for p in ws.joinpath("apkg_backups").iterdir()] == [b"old deck"]


def test_no_cards_means_deck_is_untouched(ws):
    ws.joinpath("words.txt").write_text("ignight\n", encoding="utf-8")
    ws.joinpath("output.apkg").write_bytes(b"old deck")
    run_batch(ws, batch_pipeline(), throttle=0)
    assert ws.joinpath("output.apkg").read_bytes() == b"old deck"
    assert not ws.joinpath("apkg_backups").exists()


def test_ctrl_c_saves_finished_cards_and_keeps_the_rest(ws):
    # картинки идут минутами на слово: прерванный прогон не должен выбрасывать уже сделанное
    ws.joinpath("output.apkg").write_bytes(b"old deck")
    p = batch_pipeline()
    p.suggest_spelling = lambda word: (_ for _ in ()).throw(KeyboardInterrupt())   # Ctrl+C на втором слове

    cards = run_batch(ws, p, throttle=0)

    assert [c.word for c in cards] == ["womb"]
    assert [n["fields"][0] for n in read_apkg(ws / "output.apkg")["notes"]] == ["womb"]
    assert [b.read_bytes() for b in ws.joinpath("apkg_backups").iterdir()] == [b"old deck"]
    assert lines(ws / "success_words.txt") == ["womb - My own womb sentence."]
    # прерванное слово и всё, что после него, — на следующий прогон, со своими примерами
    assert lines(ws / "words.txt") == ["ignight - My typo sentence.", "flaky"]
    assert lines(ws / "problem_words.txt") == []


def test_hard_crash_leaves_everything_intact(ws):
    before = ws.joinpath("words.txt").read_text(encoding="utf-8")
    ws.joinpath("output.apkg").write_bytes(b"old deck")
    p = batch_pipeline()
    p.suggest_spelling = lambda word: (_ for _ in ()).throw(SystemExit(1))

    with pytest.raises(SystemExit):
        run_batch(ws, p, throttle=0)

    assert ws.joinpath("words.txt").read_text(encoding="utf-8") == before
    assert ws.joinpath("output.apkg").read_bytes() == b"old deck"
    assert lines(ws / "success_words.txt") == []


def test_failed_deck_write_leaves_no_false_success(ws, monkeypatch):
    # колода пишется раньше журналов: «успех» в журнале без карточки в колоде невозможен
    before = ws.joinpath("words.txt").read_text(encoding="utf-8")

    def boom(*a, **kw):
        raise PermissionError("output.apkg is read-only")
    monkeypatch.setattr(pipeline_module.deck, "write_package", boom)

    with pytest.raises(PermissionError):
        run_batch(ws, batch_pipeline(), throttle=0)

    assert ws.joinpath("words.txt").read_text(encoding="utf-8") == before
    assert lines(ws / "success_words.txt") == [] and lines(ws / "problem_words.txt") == []


def test_unparseable_line_is_not_lost(ws, capsys):
    ws.joinpath("words.txt").write_text("... - my precious sentence\nwomb\n", encoding="utf-8")
    run_batch(ws, batch_pipeline(), throttle=0)
    assert lines(ws / "words.txt") == ["... - my precious sentence"]
    assert "Не понял строку" in capsys.readouterr().out


def test_unexpected_error_in_one_word_does_not_kill_the_batch(ws):
    p = batch_pipeline()
    original = p.lookup_cambridge
    p.lookup_cambridge = lambda w: (_ for _ in ()).throw(TypeError("markup changed")) if w == "ignight" else original(w)

    cards = run_batch(ws, p, throttle=0)

    assert [c.word for c in cards] == ["womb"]
    assert lines(ws / "words.txt") == ["ignight - My typo sentence.", "flaky"]
    assert lines(ws / "problem_words.txt") == []


def test_empty_words_txt(tmp_path):
    assert run_batch(tmp_path, batch_pipeline(), throttle=0) == []
    assert not tmp_path.joinpath("output.apkg").exists()
