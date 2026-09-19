"""Anki-колода: модель, поля карточки, запись output.apkg с бэкапом предыдущей."""
import shutil
import time
from pathlib import Path

import genanki
from colorama import Fore, Style

# Anki матчит note type ПО ID: правка полей/шаблона при реимпорте не подхватится, если тип с этим
# ID уже в коллекции. Менять шаблон — либо через содержимое полей, либо бампом ID.
# (1686681943 — старый тип без поля pic, в коллекции остаётся отдельно.)
MODEL_ID = 1686681944
DECK_ID = 1686686578
NAME = "automatic_dictionary"
FIELDS = ["word", "type", "ipa", "meaning", "example", "sound", "pic"]

MODEL = genanki.Model(
    MODEL_ID,
    NAME,
    fields=[{"name": name} for name in FIELDS],
    templates=[
        {
            "name": "Card 1",
            "qfmt": "<div style='font-family: Arial; font-size: 60px;color:#FF80DD;'>{{word}}{{sound}}</div><hr><div style='font-family: Arial; font-size: 25px;color:#79005E;'>{{type}}</div><div style='font-family: Arial; font-size: 25px;color:#AB2B52;'>{{ipa}}</div>",
            "afmt": "<div id=answer style='font-family: Arial; color:#FF80DD;'>{{FrontSide}}</div><hr><div  style='font-family: Arial; color:#00aaaa; text-align:left;'>Meaning: {{meaning}}</div><hr><div  style='font-family: Arial; color:#9CFFFA; text-align:left;'>&nbsp;→&nbsp;Example: {{example}}</div><hr><div style='font-family: Arial; text-align:center;'>{{pic}}</div>",
        },
    ],
    css=".card {font-family: arial; font-size: 20px; text-align: center; color: black; background-color: black;}\nimg {max-width: 100%;}",
)


def note_fields(card):
    """Card → значения полей в порядке FIELDS."""
    # примеры в одно поле буллетами; ведущий <br> уводит их на строку под меткой Example:
    examples_html = "".join(f"<br>• {e}" for e in card.examples)
    sound = f"[sound:{card.sound_path.name}]" if card.sound_path else ""
    pic = f"<img src='{card.collage_path.name}'>" if card.collage_path else ""
    return [card.word, card.pos, card.ipa, card.definition, examples_html, sound, pic]


def backup_existing(out_path, backup_dir):
    """Предыдущая колода — единственная копия своих примеров после очистки words.txt; молча не затирать."""
    out_path = Path(out_path)
    if not out_path.exists():
        return None
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"output-{time.strftime('%Y%m%d-%H%M%S')}.apkg"
    shutil.copy2(out_path, target)
    return target


def write_package(cards, out_path, backup_dir):
    deck = genanki.Deck(DECK_ID, NAME)
    package = genanki.Package(deck)
    for card in cards:
        deck.add_note(genanki.Note(model=MODEL, fields=note_fields(card)))
        package.media_files += [str(p) for p in (card.sound_path, card.collage_path) if p]

    backup = backup_existing(out_path, backup_dir)
    if backup:
        print(f"{Fore.CYAN}Предыдущая колода сохранена в {backup.parent.name}/{backup.name}{Style.RESET_ALL}")
    package.write_to_file(str(out_path))
