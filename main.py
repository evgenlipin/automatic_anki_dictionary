"""automatic dictionary"""

import os

# корпоративный MITM-прокси: берём системный CA-bundle, только если он реально есть,
# иначе оставляем дефолт requests (certifi) — чтобы работало и на других машинах
if not os.environ.get("REQUESTS_CA_BUNDLE") and os.path.exists("/usr/lib/ssl/cert.pem"):
    os.environ["REQUESTS_CA_BUNDLE"] = "/usr/lib/ssl/cert.pem"

import time
import shutil
import random
import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import genanki
from colorama import Fore, Style

# from create_image import create_image_collage


ua = UserAgent()
headers = {"User-Agent": ua.random}
root_dir_data = f"{os.getcwd()}/data"

REQUEST_TIMEOUT = 10   # сек на один запрос
MAX_RETRIES = 3        # попыток при сетевой ошибке
RETRY_BACKOFF = 2      # сек, линейный рост паузы между попытками
THROTTLE = 1.0         # сек паузы между словами (чтобы словари не блокировали)
EXAMPLES_COUNT = 3     # сколько примеров показывать на карточке


def fetch(url):
    """GET с ретраями на сетевых ошибках; после MAX_RETRIES пробрасывает исключение."""
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return requests.get(url, timeout=REQUEST_TIMEOUT, headers=headers)
        except requests.RequestException as exc:
            last_exc = exc
            print(f"  {Fore.YELLOW}network retry {attempt}/{MAX_RETRIES}: {exc}{Style.RESET_ALL}")
            time.sleep(RETRY_BACKOFF * attempt)
    raise last_exc


def clean_words_txt():
    """clenning words.txt"""
    with open("words.txt", "w", encoding="utf-8") as wfile:
        wfile.write("")


def get_sound_word(sound_url, word):
    """saving soundfile"""
    response_sound = fetch(sound_url)
    with open(f"{root_dir_data}/{word}.mp3", "wb") as f:
        f.write(response_sound.content)


def parser_merriam_webster(word):
    """До EXAMPLES_COUNT примеров с merriam-webster.com (fallback, если Cambridge мало)."""
    word_url = f"https://www.merriam-webster.com/dictionary/{word}"
    response_word = fetch(word_url)
    soup = BeautifulSoup(response_word.text, "lxml")
    examples = [s.text.strip() for s in soup.find_all("span", class_="ex-sent") if s.text.strip()]
    random.shuffle(examples)
    return examples[:EXAMPLES_COUNT]


def perser_cambrige(word, custom_example=None, _original_word=None):
    """parsing data of word from cambridge.org"""
    slug = word.replace(" ", "-")
    word_url = f"https://dictionary.cambridge.org/dictionary/english/{slug}"
    response_word = fetch(word_url)
    soup = BeautifulSoup(response_word.text, "lxml")

    data = soup.find("div", class_="pr entry-body__el") or soup.find("div", class_="pv-block")

    pos_tag = data.find("span", class_="pos dpos")
    if pos_tag is None:
        base_link = data.find("a", class_="Ref")
        if base_link and "/dictionary/english/" in base_link.get("href", ""):
            base_word = base_link["href"].split("/dictionary/english/")[-1].split("#")[0]
            original = _original_word or word
            print(f'  → inflected form, switching to base word "{base_word}"')
            return perser_cambrige(base_word, custom_example, _original_word=original)
        raise AttributeError(f"no pos tag and no base word link for '{word}'")

    type_word = pos_tag.text
    definition = data.find("div", class_="def ddef_d db").text

    # набираем до EXAMPLES_COUNT примеров: свой (если задан) → Cambridge → merriam
    examples = []
    if custom_example:
        examples.append(custom_example)

    for eg in data.find_all("span", class_="eg deg"):
        text = eg.text.strip()
        if text and text not in examples:
            examples.append(text)
        if len(examples) >= EXAMPLES_COUNT:
            break

    if len(examples) < EXAMPLES_COUNT:
        try:
            for text in parser_merriam_webster(_original_word or word):
                if text and text not in examples:
                    examples.append(text)
                if len(examples) >= EXAMPLES_COUNT:
                    break
        except requests.RequestException:
            pass  # merriam — необязательный fallback, сетевую ошибку тут игнорируем

    ipa_tag = data.find("span", class_="ipa dipa lpr-2 lpl-1")
    pronanciation = ipa_tag.text if ipa_tag else ""
    sound_tag = data.find("source", type="audio/mpeg") or soup.find("source", type="audio/mpeg")
    sound = sound_tag["src"]
    sound_url = f"https://dictionary.cambridge.org/{sound}"

    file_word = (_original_word or word).replace(" ", "_")
    get_sound_word(sound_url, file_word)

    return type_word, definition, examples, pronanciation


def process_word(word, custom_example=None):
    """парсинг слова; None — если слова нет в словаре (AttributeError).

    Сетевые ошибки (requests.RequestException) НЕ глотаем — пробрасываем в main,
    чтобы отличить «нет в словаре» от временного сбоя сети.
    """
    print(f'The word "{word}" is loading...')
    try:
        return perser_cambrige(word, custom_example)
    except AttributeError:
        return None


def main():
    """creating anki deck"""
    my_model = genanki.Model(
        1686681943,
        "Basic",
        fields=[
            {"name": "word"},
            {"name": "type"},
            {"name": "ipa"},
            {"name": "meaning"},
            {"name": "example"},
            {"name": "sound"},
            # {"name": "pic"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": "<div style='font-family: Arial; font-size: 60px;color:#FF80DD;'>{{word}}{{sound}}</div><hr><div style='font-family: Arial; font-size: 25px;color:#79005E;'>{{type}}</div><div style='font-family: Arial; font-size: 25px;color:#AB2B52;'>{{ipa}}</div>",
                "afmt": "<div id=answer style='font-family: Arial; color:#FF80DD;'>{{FrontSide}}</div><hr><div  style='font-family: Arial; color:#00aaaa; text-align:left;'>Meaning: {{meaning}}</div><hr><div  style='font-family: Arial; color:#9CFFFA; text-align:left;'>&nbsp;→&nbsp;Example: {{example}}</div><hr>",
            },  
        ],
        css=".card {font-family: arial; font-size: 20px; text-align: center; color: black; background-color: black;}",
    )

    my_deck = genanki.Deck(1686686578, "automatic_dictionary")

    my_package = genanki.Package(my_deck)
    problem_words = []      # слов нет в словаре → в problem_words.txt
    network_failed = []     # оригинальные строки, упавшие по сети → остаются в words.txt на ретрай

    if os.path.exists("words.txt") is False:
        print(f"{Fore.RED}'words.txt' doesn't exist{Style.RESET_ALL}")
    elif os.stat("words.txt").st_size == 0:
        print(f"{Fore.RED}'words.txt' list is empty{Style.RESET_ALL}")
    else:
        with open("words.txt", "r", encoding="utf-8") as rfile:
            lines = [line.strip() for line in rfile.readlines() if line.strip()]

        parsed = []
        for line in lines:
            if " - " in line:
                word_part, custom_example = line.split(" - ", 1)
                word_part = word_part.strip("*.,<>}{!@#$%^&()").lower().strip()
                parsed.append((word_part, custom_example.strip(), line))
            else:
                word_part = line.strip("*-.,<>}{!@#$%^&()").lower()
                parsed.append((word_part, None, line))

        for idx, (word, custom_example, line) in enumerate(parsed):
            if not word:
                continue
            if idx > 0:
                time.sleep(THROTTLE)   # пауза между словами, чтобы словари не блокировали
            if not os.path.exists(root_dir_data):
                os.makedirs(root_dir_data)

            try:
                result = process_word(word, custom_example)
            except requests.RequestException as exc:
                print(f"{Fore.YELLOW}Network error (kept in words.txt for retry): {exc}{Style.RESET_ALL}\n")
                network_failed.append(line)
                continue

            if result is None:
                print(f"{Fore.RED}Not found in dictionary{Style.RESET_ALL}\n")
                problem_words.append(word)
                continue

            type_word, definition, examples, pronounciation = result
            print(f"{Fore.GREEN}Success{Style.RESET_ALL}\n")

            # примеры в одно поле example буллетами; ведущий <br> уводит их на строку под меткой Example:
            examples_html = "<br>".join(f"• {e}" for e in examples)
            if examples_html:
                examples_html = "<br>" + examples_html

            my_note = genanki.Note(
                model=my_model,
                fields=[
                    word,
                    type_word,
                    pronounciation,
                    definition,
                    examples_html,
                    f"[sound:{word.replace(' ', '_')}.mp3]",
                ],
            )

            my_deck.add_note(my_note)
            my_package.media_files.append(f"{root_dir_data}/{word.replace(' ', '_')}.mp3")

        if problem_words:
            with open("problem_words.txt", "a", encoding="utf-8") as afile:
                for word in problem_words:
                    afile.write(f"{word}\n")
                print(f'{Fore.YELLOW}Updated "problem_words.txt"{Style.RESET_ALL}\n')
        else:
            print(f"{Fore.GREEN}Problem words didn't find{Style.RESET_ALL}\n")

        my_package.write_to_file("output.apkg")

        # сетевые сбои не теряем — оставляем в words.txt для следующего прогона
        if network_failed:
            with open("words.txt", "w", encoding="utf-8") as wfile:
                wfile.write("\n".join(network_failed) + "\n")
            print(f"{Fore.YELLOW}{len(network_failed)} word(s) kept in words.txt for retry{Style.RESET_ALL}")
        else:
            clean_words_txt()

        if os.path.exists(root_dir_data):
            shutil.rmtree(root_dir_data)
        print(f"{Fore.GREEN}The program is finished{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
