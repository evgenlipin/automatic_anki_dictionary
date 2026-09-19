"""Cambridge Dictionary — основной источник: тип, определение, IPA, примеры, озвучка."""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .. import http
from ..models import BaseRef, Entry
from . import word_exists

BASE_URL = "https://dictionary.cambridge.org"
DICT_PATH = "/dictionary/english/"
MAX_EXAMPLES = 10   # с запасом: сколько показывать, решает pipeline


def parse(html, word):
    """HTML страницы → Entry | BaseRef | None. Сети здесь нет — тестируется на сохранённых страницах."""
    soup = BeautifulSoup(html, "lxml")

    # контейнер статьи: обычное слово / фразовый глагол / идиома-фраза. Последний нужен для
    # слов, которые Cambridge ведёт как фразу внутри другой статьи (`facilities` → под `facility`).
    # Неизвестное слово редиректит на главную — там ни одного из трёх нет.
    data = (
        soup.find("div", class_="pr entry-body__el")
        or soup.find("div", class_="pv-block")
        or soup.find("div", class_="idiom-block")
    )
    if data is None:
        return None

    pos_tag = data.find("span", class_="pos dpos")
    definition_tag = data.find("div", class_="def ddef_d db")

    if pos_tag is None:
        base_link = data.find("a", class_="Ref")
        if base_link and DICT_PATH in base_link.get("href", ""):
            return BaseRef(base_link["href"].split(DICT_PATH)[-1].split("#")[0].split("?")[0])
        # идиомы/фразы (напр. «in the trenches») существуют без pos-тега, но с определением
        pos = "idiom"
    else:
        pos = pos_tag.text

    if definition_tag is None:
        return None

    # примеры в два круга: сперва блок первого значения (ближе всего к взятому определению),
    # затем вся страница — там остальные значения и фразы (`bureaucracy`: 1 в блоке против 6 на странице)
    examples = []
    for scope in (data, soup):
        for eg in scope.find_all("span", class_="eg deg"):
            text = eg.text.strip()
            if text and text not in examples:
                examples.append(text)

    ipa_tag = data.find("span", class_="ipa dipa lpr-2 lpl-1")

    # у части слов (напр. фразовых глаголов «head out») озвучки нет. Искать только внутри статьи:
    # по всей странице находится звук виджета «Word of the Day» — карточка `head out` получала
    # произношение слова `misunderstanding` (виджет есть не всегда, поэтому баг мигал)
    sound_tag = data.find("source", type="audio/mpeg")

    return Entry(
        word=word,
        pos=pos,
        # текст как есть, с хвостовым пробелом («…important: »): guid заметки у genanki — хеш всех
        # полей, и срезанный пробел превратил бы повторный импорт того же слова в дубль
        definition=definition_tag.text,
        ipa=ipa_tag.text if ipa_tag else "",
        examples=examples[:MAX_EXAMPLES],
        sound_url=urljoin(BASE_URL, sound_tag["src"]) if sound_tag else None,
        source="cambridge",
    )


def slug(word):
    """`come over` → `come-over`, `devil's advocate` → `devil-s-advocate` (так же режет сам Cambridge)."""
    return re.sub(r"[^a-z0-9]+", "-", word.lower()).strip("-")


def lookup(word):
    resp = http.get(f"{BASE_URL}{DICT_PATH}{slug(word)}")
    if not word_exists(resp):
        return None
    return parse(resp.text, word)
