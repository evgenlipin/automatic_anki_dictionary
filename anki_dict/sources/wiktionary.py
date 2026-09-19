"""Wiktionary — второй источник для слов, которых нет в Cambridge (`concurrency`, `djing`).

Даёт часть речи, определение и примеры; озвучки и IPA в этом API нет — карточка выходит без них.
Для опечаток не годится: нечёткий поиск угадал 1 из 4 (проверено 2026-09-19).
"""
from urllib.parse import quote

from bs4 import BeautifulSoup

from .. import http
from ..models import BaseRef, Entry
from . import word_exists

API_URL = "https://en.wiktionary.org/api/rest_v1/page/definition/"
MAX_EXAMPLES = 10


def _text(html):
    return " ".join(BeautifulSoup(html, "lxml").get_text().split())


def parse(payload, word):
    """JSON ответа → Entry | BaseRef | None. Берётся только английский раздел (`en`)."""
    sections = payload.get("en") or []

    first = None        # (часть речи, определение) — первое непустое
    examples = []
    for section in sections:
        for item in section.get("definitions", []):
            html = item.get("definition") or ""
            # словоформа: «simple past of misspeak» — отсылаем к базовому слову,
            # у него шанс найтись в Cambridge со звуком и IPA
            link = BeautifulSoup(html, "lxml").select_one(".form-of-definition-link a")
            if link and first is None:
                base = (link.get("title") or link.get_text()).strip()
                if base and base.lower() != word.lower():
                    return BaseRef(base)
            text = _text(html)
            if not text:
                continue
            if first is None:
                first = (section.get("partOfSpeech", "").lower(), text)
            for example in item.get("examples", []):
                example = _text(example)
                if example and example not in examples:
                    examples.append(example)

    if first is None:
        return None
    pos, definition = first
    return Entry(word=word, pos=pos, definition=definition, examples=examples[:MAX_EXAMPLES],
                 source="wiktionary")


def lookup(word):
    resp = http.get(f"{API_URL}{quote(word.replace(' ', '_'), safe='')}")   # safe='': `either/or` — одно слово
    if not word_exists(resp):
        return None
    return parse(resp.json(), word)
