"""Путь одного слова и прогон всего words.txt.

Исходов у слова три:
  Card              — карточка собрана → success_words.txt
  NotFound          — нет ни в одном словаре → problem_words.txt (с подсказкой, если это опечатка)
  исключение        — сетевой сбой или неожиданная ошибка → строка остаётся в words.txt на ретрай
"""
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests
from colorama import Fore, Style

from . import deck
from .models import BaseRef, Card, Entry, NotFound, media_name
from .wordlist import append_unique, parse_line, read_lines, with_hint, write_lines

EXAMPLES_COUNT = 3     # сколько примеров показывать на карточке
THROTTLE = 1.0         # сек паузы между словами (чтобы словари не блокировали)
MAX_HOPS = 4           # переходов словоформа → базовое слово, с запасом от зацикливания


@dataclass
class Pipeline:
    """Внешний мир передаётся функциями — в тестах подменяется без сети."""
    lookup_cambridge: Callable          # word -> Entry | BaseRef | None
    lookup_wiktionary: Callable         # word -> Entry | BaseRef | None
    generate_examples: Callable         # (word, meaning, need) -> list[str]
    suggest_spelling: Callable          # word -> str | None
    download: Callable                  # (url, path) -> None
    make_collage: Callable | None       # (media_dir, word, definition, example) -> Path | None

    def resolve(self, word):
        """Cambridge → Wiktionary; словоформа из любого источника возвращает к Cambridge по базовому слову."""
        seen = set()
        for _ in range(MAX_HOPS):
            if word in seen:
                return None
            seen.add(word)
            found = self.lookup_cambridge(word) or self.lookup_wiktionary(word)
            if isinstance(found, BaseRef):
                print(f'  → inflected form, switching to base word "{found.base_word}"')
                word = found.base_word
                continue
            return found
        return None

    def hint_for(self, word):
        """Догадка об опечатке, только если догаданное слово реально есть в словаре."""
        if len(word.split()) > 3:    # это предложение, а не слово
            return None
        try:
            candidate = self.suggest_spelling(word)
            if candidate and isinstance(self.resolve(candidate), Entry):
                return candidate
        except (requests.RequestException, ValueError):
            pass
        return None

    def collect_examples(self, request, entry):
        """Свой пример первым, затем словарные, затем добор LLM — до EXAMPLES_COUNT, без дублей."""
        examples = []
        for text in [request.custom_example, *entry.examples]:
            if text and text not in examples and len(examples) < EXAMPLES_COUNT:
                examples.append(text)

        if len(examples) < EXAMPLES_COUNT:
            try:
                need = EXAMPLES_COUNT - len(examples)
                for text in self.generate_examples(request.word, entry.definition, need):
                    if text and text not in examples and len(examples) < EXAMPLES_COUNT:
                        examples.append(text)
            except (requests.RequestException, ValueError) as exc:
                print(f"  {Fore.YELLOW}догенерация примеров не вышла: {type(exc).__name__}{Style.RESET_ALL}")
        return examples

    def process(self, request, media_dir):
        """WordRequest → Card | NotFound. Сетевой сбой словаря пробрасывается наверх."""
        print(f'The word "{request.word}" is loading...')
        entry = self.resolve(request.word)
        if entry is None:
            return NotFound(hint=self.hint_for(request.word))

        examples = self.collect_examples(request, entry)

        # файлы называются по исходному слову, а не по базовому: `bailed.mp3`, не `bail.mp3`
        media_dir = Path(media_dir)

        sound_path = None
        if entry.sound_url:
            sound_path = media_dir / f"{media_name(request.word)}.mp3"
            self.download(entry.sound_url, sound_path)

        collage_path = None
        if self.make_collage:
            first_example = examples[0] if examples else ""
            try:
                collage_path = self.make_collage(media_dir, request.word, entry.definition, first_example)
            except Exception as exc:   # картинка — украшение: никакой её сбой не должен стоить карточки
                print(f"  {Fore.YELLOW}коллаж не получился: {type(exc).__name__}{Style.RESET_ALL}")

        return Card(
            word=request.word, pos=entry.pos, ipa=entry.ipa, definition=entry.definition,
            examples=examples, source=entry.source, sound_path=sound_path, collage_path=collage_path,
        )


def _report(card):
    parts = [f"{len(card.examples)} прим."]
    parts.append("картинка" if card.collage_path else f"{Fore.YELLOW}без картинки{Fore.GREEN}")
    parts.append("звук" if card.sound_path else f"{Fore.YELLOW}без звука{Fore.GREEN}")
    source = "" if card.source == "cambridge" else f", {card.source}"
    print(f"{Fore.GREEN}Success [{card.pos}{source}]: {', '.join(parts)}{Style.RESET_ALL}\n")


def run_batch(workspace, pipeline, throttle=THROTTLE):
    """Прогнать words.txt.

    Порядок записи в конце: колода → журналы → words.txt. Упадёт запись колоды — в журналах нет
    «успехов» без карточек, а words.txt цел и прогон можно повторить.
    Ctrl+C не выбрасывает сделанное: готовые карточки пишутся, недоделанные строки остаются в words.txt.
    """
    workspace = Path(workspace)
    words_path = workspace / "words.txt"
    lines = read_lines(words_path)
    if not lines:
        print(f"{Fore.RED}'{words_path.name}' пуст или не найден в {workspace}{Style.RESET_ALL}")
        return []

    cards, success, problems, retry = [], [], [], []
    with tempfile.TemporaryDirectory() as media_dir:
        for idx, line in enumerate(lines):
            request = parse_line(line)
            if request is None:   # слово не разобралось (`... - my sentence`) — строку не теряем
                print(f"{Fore.YELLOW}Не понял строку, оставляю в words.txt: {line}{Style.RESET_ALL}\n")
                retry.append(line)
                continue
            try:
                if idx > 0:
                    time.sleep(throttle)
                result = pipeline.process(request, media_dir)
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Прервано: сохраняю {len(cards)} готовых карточек, "
                      f"остальное остаётся в words.txt{Style.RESET_ALL}")
                retry += lines[idx:]
                break
            except requests.RequestException as exc:
                print(f"{Fore.YELLOW}Network error (kept in words.txt for retry): {type(exc).__name__}{Style.RESET_ALL}\n")
                retry.append(request.raw_line)
                continue
            except Exception as exc:   # одно кривое слово не должно ронять весь список
                print(f"{Fore.RED}Unexpected {type(exc).__name__}: {exc} (kept in words.txt){Style.RESET_ALL}\n")
                retry.append(request.raw_line)
                continue

            if isinstance(result, NotFound):
                print(f"{Fore.RED}Not found in dictionary{Style.RESET_ALL}"
                      + (f" — возможно, {Fore.CYAN}{result.hint}{Style.RESET_ALL}?" if result.hint else "") + "\n")
                # исходная строка целиком: свой пример к слову-неудачнику иначе пропадает
                problems.append(with_hint(request.raw_line, result.hint))
                continue

            _report(result)
            cards.append(result)
            success.append(f"{request.word} - {request.custom_example}" if request.custom_example else request.word)

        if cards:   # пустую колоду поверх хорошей не пишем
            deck.write_package(cards, workspace / "output.apkg", workspace / "apkg_backups")
            print(f"{Fore.GREEN}output.apkg: {len(cards)} карточек{Style.RESET_ALL}")

    if success:
        added = append_unique(workspace / "success_words.txt", success)
        print(f'{Fore.CYAN}{added} слов дописано в "success_words.txt"{Style.RESET_ALL}')
    if problems:
        added = append_unique(workspace / "problem_words.txt", problems)
        print(f'{Fore.YELLOW}{added} слов дописано в "problem_words.txt"{Style.RESET_ALL}')

    write_lines(words_path, retry)
    if retry:
        print(f"{Fore.YELLOW}{len(retry)} word(s) kept in words.txt for retry{Style.RESET_ALL}")
    print(f"{Fore.GREEN}The program is finished{Style.RESET_ALL}")
    return cards
