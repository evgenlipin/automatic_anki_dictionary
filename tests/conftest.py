import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(relative):
    path = FIXTURES / relative
    if not path.exists():
        # именно fail, а не skip: пропуск дал бы зелёный итог при нуле проверенных страниц
        pytest.fail(f"нет фикстуры {relative} — скачай: docker compose run --rm fixtures", pytrace=False)
    return path.read_text(encoding="utf-8")


@pytest.fixture
def cambridge_html():
    return lambda slug: _load(f"cambridge/{slug}.html")


@pytest.fixture
def wiktionary_json():
    return lambda name: json.loads(_load(f"wiktionary/{name}.json"))


@pytest.fixture
def llm_json():
    return lambda name: json.loads(_load(f"llm/{name}.json"))
