from anki_dict.wordlist import append_unique, parse_line, read_requests, write_lines


def test_plain_word():
    req = parse_line("  Superficial \n")
    assert (req.word, req.custom_example, req.raw_line) == ("superficial", None, "Superficial")


def test_word_with_custom_example():
    req = parse_line("arrogant - I felt he came over as quite arrogant.")
    assert req.word == "arrogant"
    assert req.custom_example == "I felt he came over as quite arrogant."
    assert req.raw_line == "arrogant - I felt he came over as quite arrogant."


def test_example_keeps_its_own_dashes():
    req = parse_line("come over - He came over - finally - as arrogant.")
    assert (req.word, req.custom_example) == ("come over", "He came over - finally - as arrogant.")


def test_hyphen_inside_word_survives():
    assert parse_line("well-being").word == "well-being"
    assert parse_line("-well-being-").word == "well-being"


def test_punctuation_is_stripped():
    assert parse_line("*womb*,").word == "womb"


def test_hint_tail_is_ignored():
    req = parse_line("ignight   # возможно: ignite")
    assert (req.word, req.raw_line) == ("ignight", "ignight")


def test_hash_inside_example_is_not_a_hint():
    assert parse_line("rank - She is #1 in the rank.").custom_example == "She is #1 in the rank."
    # ` # ` с пробелами по бокам — тоже не подсказка: отрезается только собственный маркер
    req = parse_line("hash - Press the # key to continue.")
    assert req.custom_example == "Press the # key to continue."
    assert req.raw_line == "hash - Press the # key to continue."


def test_bom_does_not_stick_to_first_word(tmp_path):
    path = tmp_path / "words.txt"
    path.write_bytes("﻿womb\ncrux\n".encode("utf-8"))
    assert [r.word for r in read_requests(path)] == ["womb", "crux"]


def test_empty_and_wordless_lines():
    assert parse_line("") is None
    assert parse_line("   ") is None
    assert parse_line("***") is None


def test_read_requests(tmp_path):
    path = tmp_path / "words.txt"
    path.write_text("superficial\n\narrogant - He is arrogant.\n\n\n", encoding="utf-8")
    assert [r.word for r in read_requests(path)] == ["superficial", "arrogant"]
    assert read_requests(tmp_path / "missing.txt") == []


def test_append_unique_skips_duplicates(tmp_path):
    path = tmp_path / "journal.txt"
    assert append_unique(path, ["womb", "bail - He bailed.", "womb"]) == 2
    assert append_unique(path, ["womb", "crux"]) == 1
    assert path.read_text(encoding="utf-8").splitlines() == ["womb", "bail - He bailed.", "crux"]


def test_append_unique_ignores_hint_when_comparing(tmp_path):
    path = tmp_path / "problem_words.txt"
    path.write_text("ignight\n", encoding="utf-8")
    assert append_unique(path, ["ignight   # возможно: ignite"]) == 0
    assert append_unique(path, ["marmaid   # возможно: mermaid"]) == 1
    assert append_unique(path, ["marmaid"]) == 0


def test_journal_line_roundtrips_into_words_txt(tmp_path):
    # строку из журнала можно вернуть во вход как есть — со своим примером и без потерь
    journal = tmp_path / "problem_words.txt"
    append_unique(journal, ["concurrency - What is the peak concurrency?   # возможно: concurrent"])
    req = read_requests(journal)[0]
    assert (req.word, req.custom_example) == ("concurrency", "What is the peak concurrency?")


def test_write_lines_clears_and_keeps(tmp_path):
    path = tmp_path / "words.txt"
    write_lines(path, ["a", "b - c"])
    assert path.read_text(encoding="utf-8") == "a\nb - c\n"
    write_lines(path, [])
    assert path.read_text(encoding="utf-8") == ""
    assert [p.name for p in tmp_path.iterdir()] == ["words.txt"]   # временный файл не остаётся
