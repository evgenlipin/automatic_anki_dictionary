"""Текстовый LLM (text.pollinations.ai): добор примеров и догадка об опечатке."""
import re
import time

from . import http

LLM_URL = "https://text.pollinations.ai/openai"
LLM_MODEL = "openai-fast"
TEXTGEN_TIMEOUT = 60   # сек на один ответ
EMPTY_RETRY_PAUSE = 3

_BULLET = re.compile(r"^\s*[-*\d.)]+\s*")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"“])")


def ask_llm(prompt, token=None, timeout=90, effort="low"):
    """Запрос через OpenAI-совместимый POST → чистый текст ответа ("" если модель промолчала).

    GET-эндпоинт `text.pollinations.ai/<prompt>` использовать НЕЛЬЗЯ: модель reasoning-овая и
    отдаёт JSON со своим внутренним монологом, который уезжал прямо в промпт картинки.

    `reasoning_effort` обязателен. Без него модель может потратить на размышления весь лимит
    ответа (1500 токенов) и вернуть пустой `content` — так выглядели «сцены от LLM: 0/4».
    Замер 2026-09-19 на промпте сцен: `come over` без параметра 1500 токенов → пусто,
    medium — 600-950 и сцены связнее, low — 120-150 и не пустеет никогда, но сцены проще.
    Поэтому: первая попытка с заданным effort, повтор на пустой ответ — всегда с low.
    """
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    for attempt in range(2):
        resp = http.post(
            LLM_URL, headers=headers, timeout=timeout, retries=1, quiet=True,
            json={"model": LLM_MODEL, "reasoning_effort": effort if attempt == 0 else "low",
                  "messages": [{"role": "user", "content": prompt}]},
        )
        resp.raise_for_status()
        try:
            content = (resp.json()["choices"][0]["message"].get("content") or "").strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"неожиданный ответ LLM: {type(exc).__name__}") from exc
        if content:
            return content
        if attempt == 0:
            time.sleep(EMPTY_RETRY_PAUSE)
    return ""


def clean_lines(text):
    """Ответ LLM → строки без нумерации, маркеров и кавычек."""
    out = []
    for line in text.splitlines():
        line = _BULLET.sub("", line.strip().strip('"').strip()).strip().strip('"').strip()
        if line:
            out.append(line)
    return out


def examples_prompt(word, meaning, need):
    return (
        f'Write exactly {need} short natural English example sentence(s) using the word "{word}"'
        + (f' meaning "{meaning}"' if meaning else "")
        + ". One sentence per line. No numbering, no quotes, no extra text."
    )


def generate_examples(word, meaning, need, token=None):
    """Догенерировать `need` примеров.

    Зачем не словарь: у Cambridge для части слов физически 1-2 примера на всей странице
    (`womb` — один), а merriam (403) и dictionaryapi.dev (522) мертвы.
    """
    # просим на один больше: модель нет-нет да повторит словарный пример, и после отсева дублей
    # в pipeline до трёх не хватало бы. Лишнее pipeline отбросит сам.
    # medium: с low модель пишет корявые фразы («fell over in a squealer») и клеит их в одну строку;
    # на коротком промпте medium стоит 230-450 токенов — до лимита в 1500 далеко
    answer = ask_llm(examples_prompt(word, meaning, need + 1), token, timeout=TEXTGEN_TIMEOUT, effort="medium")
    lines = clean_lines(answer)
    if len(lines) < need:
        # модель иногда кладёт все предложения в одну строку (`misspoke`: два через пробел) —
        # карточка выходила с двумя буллетами, второй из которых был двойным
        lines = [s.strip() for line in lines for s in _SENTENCE_END.split(line)]
    # отсекаем болтовню модели («Sure! Here are your sentences:»): берём законченные предложения.
    # Сначала те, где слово стоит буквально; формы вроде «came over» для `come over` — следом,
    # раньше они отсеивались совсем и примеров выходило меньше трёх
    sentences = [l for l in lines if len(l) > 10 and l[-1] in ".!?\"”'"]
    stem = word.split()[0].lower()
    literal = [l for l in sentences if stem in l.lower()]
    return literal + [l for l in sentences if l not in literal]


def spelling_prompt(word):
    return (
        f'"{word}" is probably a misspelled English word. Reply with the single most likely '
        "correct word only, lowercase. If you are not sure, reply with ?"
    )


def suggest_spelling(word, token=None):
    """Догадка, какое слово имелось в виду; None, если модель не уверена.

    Это только кандидат: существует ли он в словаре, проверяет pipeline — без проверки
    подсказку в журнал не пишем.
    """
    lines = clean_lines(ask_llm(spelling_prompt(word), token, timeout=TEXTGEN_TIMEOUT))
    if not lines:
        return None
    candidate = lines[0].strip(" .,!?\"'").lower()
    if not candidate or candidate == word.lower() or not re.fullmatch(r"[a-z][a-z' -]*", candidate):
        return None
    if len(candidate.split()) > 3:   # модель ответила фразой, а не словом
        return None
    return candidate
