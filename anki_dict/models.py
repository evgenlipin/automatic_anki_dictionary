"""Структуры данных, которыми обмениваются модули."""
import re
from dataclasses import dataclass, field
from pathlib import Path


def media_name(word):
    """Слово → основа имени медиафайла: `come over` → `come_over`, `devil's advocate` → `devil_s_advocate`.

    Апостроф и прочее нельзя: имя уходит в `<img src='…'>`, кавычка внутри рвёт атрибут.
    Для обычных слов результат тот же, что у прежнего `replace(" ", "_")`.
    """
    return re.sub(r"[^a-z0-9_-]", "_", word.lower())


@dataclass
class WordRequest:
    """Одна строка words.txt."""
    word: str                   # очищенное слово в нижнем регистре
    custom_example: str | None  # свой пример после ` - `
    raw_line: str               # исходная строка без хвоста-подсказки: её можно вернуть во вход как есть


@dataclass
class Entry:
    """Что отдал словарь."""
    word: str
    pos: str
    definition: str
    ipa: str = ""
    examples: list[str] = field(default_factory=list)
    sound_url: str | None = None
    source: str = "cambridge"   # cambridge | wiktionary


@dataclass
class BaseRef:
    """Словоформа: словарь отсылает к базовому слову (`bailed` → `bail`)."""
    base_word: str


@dataclass
class Card:
    """Готовая карточка: поля + пути к медиа."""
    word: str
    pos: str
    ipa: str
    definition: str
    examples: list[str]
    source: str
    sound_path: Path | None = None
    collage_path: Path | None = None


@dataclass
class NotFound:
    """Слова нет ни в одном словаре; hint — проверенная по словарю догадка об опечатке."""
    hint: str | None = None
