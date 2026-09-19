"""Колода собирается по-настоящему и вскрывается как zip + sqlite — без Anki."""
from anki_dict import deck
from anki_dict.inspect_apkg import broken_refs, read_apkg
from anki_dict.models import Card


def _card(tmp_path, word, with_media=True, examples=("One.", "Two.", "Three.")):
    safe = word.replace(" ", "_")
    sound = collage = None
    if with_media:
        sound = tmp_path / f"{safe}.mp3"
        sound.write_bytes(b"mp3")
        collage = tmp_path / f"collage_{safe}.jpg"
        collage.write_bytes(b"jpg")
    return Card(word=word, pos="noun", ipa="wuːm", definition="a definition:", examples=list(examples),
                source="cambridge", sound_path=sound, collage_path=collage)


def test_note_fields_order_and_format(tmp_path):
    fields = deck.note_fields(_card(tmp_path, "come over"))
    assert fields == [
        "come over", "noun", "wuːm", "a definition:",
        "<br>• One.<br>• Two.<br>• Three.",
        "[sound:come_over.mp3]",
        "<img src='collage_come_over.jpg'>",
    ]


def test_note_fields_without_media(tmp_path):
    fields = deck.note_fields(_card(tmp_path, "djing", with_media=False, examples=()))
    assert fields[4:] == ["", "", ""]


def test_package_contents(tmp_path):
    out = tmp_path / "ws" / "output.apkg"
    out.parent.mkdir()
    deck.write_package([_card(tmp_path, "womb"), _card(tmp_path, "djing", with_media=False)],
                       out, out.parent / "apkg_backups")

    apkg = read_apkg(out)
    assert len(apkg["notes"]) == 2
    # Anki матчит тип заметки по ID: смена ID = другой тип, старые карточки перестанут обновляться
    assert {n["mid"] for n in apkg["notes"]} == {1686681944}
    assert all(len(n["fields"]) == 7 for n in apkg["notes"])
    assert apkg["media"] == {"womb.mp3", "collage_womb.jpg"}
    assert broken_refs(apkg) == []


def test_broken_refs_are_detected(tmp_path):
    card = _card(tmp_path, "womb")
    fields = deck.note_fields(card)
    apkg = {"notes": [{"mid": 1, "fields": fields}], "media": {"womb.mp3"}}
    assert broken_refs(apkg) == [("womb", "collage_womb.jpg")]


def test_previous_deck_is_backed_up_before_overwrite(tmp_path):
    out = tmp_path / "output.apkg"
    backups = tmp_path / "apkg_backups"
    out.write_bytes(b"old deck with hand-typed examples")

    deck.write_package([_card(tmp_path, "womb")], out, backups)

    saved = list(backups.glob("output-*.apkg"))
    assert len(saved) == 1
    assert saved[0].read_bytes() == b"old deck with hand-typed examples"
    assert out.read_bytes() != b"old deck with hand-typed examples"


def test_first_run_has_nothing_to_back_up(tmp_path):
    deck.write_package([_card(tmp_path, "womb")], tmp_path / "output.apkg", tmp_path / "apkg_backups")
    assert not (tmp_path / "apkg_backups").exists()
