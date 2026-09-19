"""Картинки через pollinations.ai и сборка коллажа.

Картинка — необязательное украшение карточки: любые сбои здесь глотаются, слово всё равно собирается.
"""
import re
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image

from . import http
from .llm import ask_llm, clean_lines
from .models import media_name

IMG_URL = "https://image.pollinations.ai/prompt/"
IMG_TIMEOUT = 120     # сек на одну картинку
IMG_RETRIES = 3       # попыток на картинку
IMG_BACKOFF = 3       # сек, линейный рост паузы между попытками
SLOT_W = 400          # ширина одной картинки в коллаже
WATERMARK_CROP = 0.10 # доля высоты снизу под срез водяного знака pollinations
SCENES = 4

# Общий хвост промпта: только то, что ДОЛЖНО быть на картинке. За «sana» у pollinations стоит
# DreamShaper (Stable Diffusion 1.5) — отрицаний он не понимает: «no nudity» в промпте для него
# просто слово «nudity». Запреты идут отдельным параметром negative_prompt (проверено 2026-09-19:
# параметр действует — та же пара промпт+seed даёт другую картинку; на 12 картинках трёх классов
# слов качество не хуже прежнего. Что это лечит обнажёнку — НЕ доказано: на пробе её не было ни
# в одном варианте).
STYLE = ("clean educational digital illustration, single clear subject, strong focal point, "
         "simple uncluttered background, soft natural light, people wearing everyday clothes")
NEGATIVE = ("nudity, naked, nsfw, topless, cleavage, underwear, "
            "text, letters, words, watermark, logo, split frames, collage")


def _short(exc):
    """Короткая причина сбоя без гигантского URL (500, timeout, proxy 503 …)."""
    text = str(exc)
    for marker in ("500 Server Error", "502 Server Error", "503 Server Error", "429"):
        if marker in text:
            return marker
    if "Tunnel connection failed" in text or "Unable to connect to proxy" in text:
        return "прокси недоступен"
    if "timed out" in text or "Timeout" in text:
        return "таймаут"
    return type(exc).__name__


def clean_definition(definition):
    """Определение словаря → пригодный для промпта кусок.

    Сырое определение тащит служебный хвост (`:`), глоссы в скобках `(= ...)` и
    перечисления через `;` — всё это модель рисует буквально и картинка плывёт.
    """
    text = re.sub(r"\([^)]*\)", " ", definition)       # скобки, включая (= пояснение)
    text = text.split(";")[0]                          # первое значение из перечисления
    text = text.replace(":", " ").strip(" .,")
    text = re.sub(r"\s+", " ", text)
    return text[:160]


def scenes_prompt(word, meaning, example_sentence):
    return (
        f'Word: "{word}". Meaning: {meaning}. Example: "{example_sentence}".\n'
        "Describe 4 different images that teach this word. Vary them: the thing itself, "
        "the example as a scene, an everyday situation, a close-up detail. "
        "Describe only PHYSICAL things: concrete objects, people doing a visible action, places. "
        "Never describe emotions, states or abstractions — name the objects and the action instead. "
        # без этого «the thing itself» для абстрактных слов превращается в надпись: «ENRAGED in neon letters»
        "Never show the word as written text or letters. "
        "Family-friendly and safe for work. "
        "One image per line, max 20 words each, no numbering."
    )


def parse_scenes(answer):
    return [line for line in clean_lines(answer) if len(line) > 15][:SCENES]


def build_prompts(word, definition, example_sentence, token=None):
    """4 РАЗНЫХ ракурса, все про одно слово. Сюжеты пишет LLM, шаблон — запасной путь."""
    meaning = clean_definition(definition)

    try:
        # medium: сцены заметно связнее, чем с low; если ответ опустеет — ask_llm повторит с low
        answer = ask_llm(scenes_prompt(word, meaning, example_sentence), token, effort="medium")
        scenes = parse_scenes(answer)
        if len(scenes) >= 3:
            return [f"{s}. {STYLE}" for s in scenes]
        reason = f"получено {len(scenes)}/{SCENES}" if answer else "пустой ответ"
        print(f"    сцены от LLM: {reason}, беру шаблонные")
    except (requests.RequestException, ValueError) as exc:
        print(f"    сцены от LLM недоступны ({_short(exc)}), беру шаблонные")

    subject = f'the concept of "{word}" ({meaning})' if meaning else f'the concept of "{word}"'
    return [
        # 1. само понятие крупно и буквально
        f"{subject}. The {word} itself is the main subject, centered, large and unmistakable. {STYLE}",
        # 2. сцена из примера, но слово — то, ради чего кадр
        (f'Scene illustrating this sentence: "{example_sentence}". '
         f'The meaning of "{word}" ({meaning}) must be the visual focus of the scene. {STYLE}')
        if example_sentence else
        f'A person clearly demonstrating "{word}" ({meaning}). {STYLE}',
        # 3. типичная жизненная ситуация употребления
        f'A everyday real-life situation where "{word}" ({meaning}) is happening, '
        f"shown through what people are doing. {STYLE}",
        # 4. контрастный ракурс — крупный план ключевой детали
        f'Close-up view of the key detail that conveys "{word}" ({meaning}), '
        f"minimal composition, one object or one gesture. {STYLE}",
    ]


def crop_watermark(image):
    """pollinations штампует лого в правом нижнем углу, `nologo=true` его больше не убирает
    (проверено 2026-09, с токеном) — единственный рабочий способ: срезать нижнюю полосу."""
    rgb = image.convert("RGB")
    w, h = rgb.size
    return rgb.crop((0, 0, w, int(h * (1 - WATERMARK_CROP))))


def get_image(prompt, out_path, token, seed):
    """Скачивает одну картинку. True/False по успеху."""
    # параметра model нет намеренно: доступна одна `sana`, значение игнорируется
    url = (f"{IMG_URL}{quote(prompt)}?width=512&height=512&nologo=true&safe=true&seed={seed}"
           f"&negative_prompt={quote(NEGATIVE)}")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    last_exc = None
    for attempt in range(1, IMG_RETRIES + 1):
        try:
            resp = http.get(url, headers=headers, timeout=IMG_TIMEOUT, retries=1, quiet=True)
            resp.raise_for_status()
            with Image.open(BytesIO(resp.content)) as image:
                crop_watermark(image).save(out_path)
            return True
        except (requests.RequestException, OSError) as exc:
            last_exc = exc
            # короткая причина без полного URL — это всего лишь повтор, который обычно проходит
            print(f"    ⟳ картинка {seed}/{SCENES}: попытка {attempt}/{IMG_RETRIES} ({_short(exc)})")
            time.sleep(IMG_BACKOFF * attempt)
    print(f"    ✗ картинка {seed}/{SCENES} не получилась: {_short(last_exc)}")
    return False


def create_collage(image_paths, out_path):
    """Горизонтальный коллаж из скачанных картинок (от одной до четырёх)."""
    imgs = []
    for path in image_paths:
        with Image.open(path) as original:
            original = original.convert("RGB")
            width, height = original.size
            imgs.append(original.resize((SLOT_W, int(SLOT_W * height / width))))

    collage = Image.new("RGB", (SLOT_W * len(imgs), max(im.size[1] for im in imgs)), (0, 0, 0))
    for idx, im in enumerate(imgs):
        collage.paste(im, (SLOT_W * idx, 0))
    collage.save(out_path)
    return out_path


def create_image_collage(media_dir, word, definition, example_sentence, token=None):
    """4 картинки → коллаж. Путь к collage_{word}.jpg или None, если ничего не сгенерилось."""
    media_dir = Path(media_dir)
    safe = media_name(word)
    prompts = build_prompts(word, definition, example_sentence, token)

    throttle = 5 if token else 15   # rate limit pollinations: Seed (токен) 1/5с, аноним 1/15с
    saved = []
    for i, prompt in enumerate(prompts, 1):
        if i > 1:
            time.sleep(throttle)
        path = media_dir / f"_{safe}{i}.png"
        if get_image(prompt, path, token, seed=i):
            saved.append(path)

    if not saved:
        return None
    collage_path = create_collage(saved, media_dir / f"collage_{safe}.jpg")
    for path in saved:
        path.unlink(missing_ok=True)
    return collage_path
