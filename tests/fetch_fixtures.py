"""Скачать настоящие ответы словарей в tests/fixtures/ — как пришли, без обработки.

    docker compose run --rm fixtures          страницы Cambridge и Wiktionary (в git не лежат)
    docker compose run --rm fixtures --llm    только ответы LLM (лежат в git, перезаписываются)

Выдуманный HTML проверял бы мои представления о словаре, а не словарь — поэтому только настоящие.
"""
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from anki_dict import http, images, llm  # noqa: E402

ROOT = Path(__file__).resolve().parent / "fixtures"
PAUSE = 2   # сек между запросами — не долбить словари

# чем ценен каждый экземпляр — в tests/fixtures/README.md
CAMBRIDGE = ["superficial", "come-over", "facilities", "in-the-trenches", "bailed",
             "head-out", "womb", "ignight", "concurrency"]
WIKTIONARY = ["concurrency", "misspoke", "ignight", "squealer", "djing", "bail"]

# промпты — те же функции, что в боевом коде: фикстура показывает ответ на настоящий запрос
LOW = {"reasoning_effort": "low"}   # как в боевом ask_llm
LLM_PROMPTS = {
    "examples": (llm.examples_prompt(
        "womb", "the organ in the body of a woman in which a baby develops before birth", 2), LOW),
    "spelling": (llm.spelling_prompt("ignight"), LOW),
    "scenes": (images.scenes_prompt(
        "enraged", "very angry", "He was enraged at the article about him."), LOW),
}


def save(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    print(f"  {path.relative_to(ROOT)}  {len(content)} байт")


def fetch_llm():
    token = os.environ.get("POLLINATIONS_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    for name, (prompt, extra) in LLM_PROMPTS.items():
        resp = http.post(
            llm.LLM_URL, headers=headers, timeout=120,
            json={"model": llm.LLM_MODEL, "messages": [{"role": "user", "content": prompt}], **extra},
        )
        save(ROOT / "llm" / f"{name}.json", json.dumps(resp.json(), ensure_ascii=False, indent=1).encode())
        time.sleep(5)


def main():
    if "--llm" in sys.argv:
        return fetch_llm()

    for slug in CAMBRIDGE:
        resp = http.get(f"https://dictionary.cambridge.org/dictionary/english/{slug}")
        save(ROOT / "cambridge" / f"{slug}.html", resp.content)
        time.sleep(PAUSE)

    for word in WIKTIONARY:
        resp = http.get(f"https://en.wiktionary.org/api/rest_v1/page/definition/{quote(word)}")
        save(ROOT / "wiktionary" / f"{word}.{resp.status_code}.json", resp.content)
        time.sleep(PAUSE)


if __name__ == "__main__":
    main()
