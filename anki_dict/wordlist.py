"""words.txt и журналы: разбор строк, запись без дублей.

Формат строки один на вход и на оба журнала: `слово` или `слово - свой пример`.
В problem_words.txt к строке может быть дописана подсказка `   # возможно: ignite` —
при разборе она отбрасывается, поэтому строку можно вернуть в words.txt как есть.
"""
import os
import re
from pathlib import Path

from .models import WordRequest

HINT_MARK = "# возможно:"
# только собственный маркер: просто ` # ` встречается в своих примерах («Press the # key»)
_HINT_TAIL = re.compile(r"\s+" + re.escape(HINT_MARK) + r".*$")
_STRIP = "*.,<>}{!@#$%^&()"


def with_hint(line, hint):
    return f"{line}   {HINT_MARK} {hint}" if hint else line


def strip_hint(line):
    return _HINT_TAIL.sub("", line).strip()


def parse_line(line):
    """Строка → WordRequest; None для пустой строки и строки без слова."""
    raw = strip_hint(line)
    if not raw:
        return None
    if " - " in raw:
        word_part, custom_example = raw.split(" - ", 1)
        word = word_part.strip(_STRIP).lower().strip()
        custom_example = custom_example.strip() or None
    else:
        # дефис срезается только по краям: `well-being` остаётся целым
        word = raw.strip(_STRIP + "-").lower().strip()
        custom_example = None
    if not word:
        return None
    return WordRequest(word=word, custom_example=custom_example, raw_line=raw)


def read_lines(path):
    """Непустые строки файла. utf-8-sig: BOM от Windows-редактора иначе прилипает к первому слову."""
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig") as f:
        return [line.strip() for line in f if line.strip()]


def read_requests(path):
    parsed = (parse_line(line) for line in read_lines(path))
    return [req for req in parsed if req]


def append_unique(path, lines):
    """Дописать в журнал только строки, которых там ещё нет. Возвращает число добавленных.

    Сравнение — без хвоста-подсказки: `ignight` и `ignight   # возможно: ignite` это одна запись.
    """
    path = Path(path)
    existing = set()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            existing = {strip_hint(l) for l in f if l.strip()}
    new = []
    for line in lines:
        key = strip_hint(line)
        if key and key not in existing:
            existing.add(key)
            new.append(line)
    if new:
        with open(path, "a", encoding="utf-8") as f:
            f.write("".join(f"{line}\n" for line in new))
    return len(new)


def write_lines(path, lines):
    """Перезаписать words.txt оставшимися строками (пустой список — очистить).

    Через временный файл + replace: обрыв посреди записи не оставит words.txt обрезанным.
    """
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("".join(f"{line}\n" for line in lines))
    os.replace(tmp, path)
