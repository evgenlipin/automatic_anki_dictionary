# Фикстуры — настоящие ответы, как пришли

Скачать: `docker compose run --rm fixtures` (словари), `docker compose run --rm fixtures --llm` (LLM).
Посмотреть, что из них достают парсеры: `docker compose run --rm --entrypoint python test tests/show_parsed.py`.

`cambridge/` и `wiktionary/` в git не лежат (чужой контент, репозиторий публичный). Без них тесты
**падают** с подсказкой, а не пропускаются. `llm/` — в git: это ответы на наши же промпты.

## cambridge/ — по одной странице на каждый вид статьи

| Файл | Чем ценен |
|---|---|
| `superficial.html` | обычное слово: `div.pr.entry-body__el`, pos, IPA, звук, 10+ примеров |
| `come-over.html` | фразовый глагол: `div.pv-block` |
| `facilities.html` | `div.idiom-block` — фраза внутри чужой статьи (`facility`), первых двух контейнеров нет |
| `in-the-trenches.html` | идиома: pos-тега нет вовсе, но определение есть → `pos = "idiom"` |
| `bailed.html` | словоформа: нет pos, есть `a.Ref` на базовое слово → `BaseRef("bail")` |
| `head-out.html` | нет озвучки и только 2 примера → добор через LLM |
| `womb.html` | один пример на всю страницу |
| `ignight.html` | неизвестное слово: Cambridge редиректит на главную → `None` |
| `concurrency.html` | статьи нет, только корпусная страница «Examples of …» → `None` |

## wiktionary/

| Файл | Чем ценен |
|---|---|
| `concurrency.200.json` | обычная статья; определения с HTML-разметкой, примеров нет |
| `misspoke.200.json` | словоформа: `form-of-definition-link` → `BaseRef("misspeak")` |
| `ignight.404.json` | тело ответа 404 — до разбора доходить не должно |

## llm/ — ответы `text.pollinations.ai/openai` с `reasoning_effort: low`

| Файл | Чем ценен |
|---|---|
| `examples.json` | два примера; у строк хвостовые пробелы перед переносом |
| `spelling.json` | догадка об опечатке: `ignight` → `ignite` |
| `scenes.json` | 4 сцены для картинок, между строками пустые строки |

Пустой `content` (случай «сцены от LLM: 0/4») по заказу не воспроизводится — в тестах он собран
из `scenes.json` заменой `content` на `""`: в наблюдавшемся ответе отличалось только это.
