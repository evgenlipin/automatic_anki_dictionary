"""automatic dictionary"""

import os
os.environ.setdefault("REQUESTS_CA_BUNDLE", "/usr/lib/ssl/cert.pem")

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


def clean_words_txt():
    """clenning words.txt"""
    with open("words.txt", "w", encoding="utf-8") as wfile:
        wfile.write("")


def get_sound_word(sound_url, word):
    """saving soundfile"""
    response_sound = requests.get(sound_url, timeout=5, headers=headers)
    with open(f"{root_dir_data}/{word}.mp3", "wb") as f:
        f.write(response_sound.content)


def parser_merriam_webster(word):
    """parsing examples from merriam-webster.com"""
    word_url = f"https://www.merriam-webster.com/dictionary/{word}"
    response_word = requests.get(word_url, timeout=10, headers=headers)
    soup = BeautifulSoup(response_word.text, "lxml")
    examples = [s.text.strip() for s in soup.find_all("span", class_="ex-sent") if s.text.strip()]
    return random.choice(examples) if examples else ""


def perser_cambrige(word, custom_example=None, _original_word=None):
    """parsing data of word from cambridge.org"""
    slug = word.replace(" ", "-")
    word_url = f"https://dictionary.cambridge.org/dictionary/english/{slug}"
    response_word = requests.get(word_url, timeout=5, headers=headers)
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
    if custom_example:
        example_sentence = custom_example
    else:
        try:
            example_sentence = data.find("span", class_="eg deg").text
        except AttributeError:
            example_sentence = parser_merriam_webster(_original_word or word)
    ipa_tag = data.find("span", class_="ipa dipa lpr-2 lpl-1")
    pronanciation = ipa_tag.text if ipa_tag else ""
    sound_tag = data.find("source", type="audio/mpeg") or soup.find("source", type="audio/mpeg")
    sound = sound_tag["src"]
    sound_url = f"https://dictionary.cambridge.org/{sound}"

    file_word = (_original_word or word).replace(" ", "_")
    get_sound_word(sound_url, file_word)

    return type_word, definition, example_sentence, pronanciation


def process_word(word, custom_example=None):
    """creating image and saving it in data folder"""
    print(f'The word "{word}" is loading...')
    try:
        type_word, definition, example_sentence, pronanciation = perser_cambrige(word, custom_example)
    except AttributeError:
        return None

    # create_image_collage(root_dir_data, word, definition, example_sentence)

    return type_word, definition, example_sentence, pronanciation


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
    problem_words = []

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
                parsed.append((word_part, custom_example.strip()))
            else:
                word_part = line.strip("*-.,<>}{!@#$%^&()").lower()
                parsed.append((word_part, None))

        for word, custom_example in parsed:
            if word:
                try:
                    if not os.path.exists(root_dir_data):
                        os.makedirs(root_dir_data)
                    type_word, definition, example_sentence, pronounciation = process_word(word, custom_example)
                    print(f"{Fore.GREEN}Success{Style.RESET_ALL}\n")
                except TypeError:
                    print(f"{Fore.RED}Processing Error{Style.RESET_ALL}\n")
                    problem_words.append(word)
                    continue

                my_note = genanki.Note(
                    model=my_model,
                    fields=[
                        word,
                        type_word,
                        pronounciation,
                        definition,
                        example_sentence,
                        f"[sound:{word.replace(' ', '_')}.mp3]",
                        # f"<img src='collage_{word}.jpg'>",
                    ],
                )

                my_deck.add_note(my_note)
                my_package.media_files.append(f"{root_dir_data}/{word.replace(' ', '_')}.mp3")
                # my_package.media_files.append(f"{root_dir_data}/collage_{word}.jpg")

        if problem_words:
            with open("problem_words.txt", "a", encoding="utf-8") as afile:
                for word in problem_words:
                    afile.write(f"{word}\n")
                print(f'{Fore.YELLOW}Created "problem_words.txt"{Style.RESET_ALL}\n')
        else:
            print(f"{Fore.GREEN}Problem words didn't find{Style.RESET_ALL}\n")

        my_package.write_to_file("output.apkg")
        clean_words_txt()
        shutil.rmtree(root_dir_data)
        print(f"{Fore.GREEN}The program is finished{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
