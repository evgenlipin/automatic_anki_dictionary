"""Показать, что парсеры достают из сохранённых страниц — чтобы сверить глазами с сайтом.

    docker compose run --rm --entrypoint python test tests/show_parsed.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from anki_dict.sources import cambridge, wiktionary  # noqa: E402

ROOT = Path(__file__).resolve().parent / "fixtures"

for path in sorted((ROOT / "cambridge").glob("*.html")):
    print(f"\n=== cambridge/{path.name}")
    print(cambridge.parse(path.read_text(encoding="utf-8"), path.stem.replace("-", " ")))

for path in sorted((ROOT / "wiktionary").glob("*.200.json")):
    print(f"\n=== wiktionary/{path.name}")
    print(wiktionary.parse(json.loads(path.read_text(encoding="utf-8")), path.name.split(".")[0]))
