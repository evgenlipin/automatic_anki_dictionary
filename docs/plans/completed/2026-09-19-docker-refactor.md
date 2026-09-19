# Переезд на пакет + Docker + тесты + второй источник

Дата: 2026-09-19. Статус: реализовано и проверено, не закоммичено (ветка `docker-refactor`).

## Цель

1. Код разложен по ролям, понятно где что лежит (`anki_dict/`).
2. Запуск и тесты — через Docker одной командой, без пробных скриптов и аппрувов.
3. Тесты без сети на настоящих страницах словарей.
4. Слова, которых нет в Cambridge, берутся из Wiktionary; для опечаток — подсказка.

**Не меняется:** формат `words.txt` и журналов, ID модели `1686681944` и колоды `1686686578`,
поля и шаблон карточки, три исхода слова (успех / нет в словаре / сетевой сбой),
бэкап `output.apkg` перед перезаписью.

## Решения (согласованы)

| Вопрос | Решение |
|---|---|
| Как пользоваться | Как сейчас: `words.txt` → одна команда → `output.apkg`, импорт руками |
| Слова вне Cambridge | Wiktionary как второй источник (карточка без звука/IPA) |
| Опечатки | Только подсказка `ignight   # возможно: ignite`, без автозамены |
| Структура | Пакет по ролям + тонкий CLI (вариант A) |
| Данные | `workspace/` (боевые), `.sandbox/` (мои прогоны), обе вне git |
| Код в контейнере | Монтируется; образ = только зависимости |
| Фикстуры словарей | Лежат локально, в git не идут (репо публичный, контент Cambridge); скачиваются командой |

## Целевая структура

```
anki_dict/
  __main__.py     python -m anki_dict
  cli.py          команды run (по умолчанию) / inspect; флаги --no-images, --workspace
  wordlist.py     WordRequest, разбор строк, append_unique, журналы
  http.py         fetch с ретраями, одна SSL-политика
  sources/
    cambridge.py  parse(html) -> Entry | BaseRef | None ; lookup(word)
    wiktionary.py parse(json) -> Entry | BaseRef | None ; lookup(word)
  llm.py          ask_llm, generate_examples, suggest_spelling
  images.py       сцены, скачивание, коллаж (перенос create_image.py)
  deck.py         модель Anki, HTML полей, запись apkg + бэкап
  pipeline.py     process(WordRequest) -> Card | NotFound ; сетевой сбой пробрасывается
tests/
  fixtures/cambridge/*.html  fixtures/wiktionary/*.json  fixtures/llm/*.json
workspace/   words.txt success_words.txt problem_words.txt output.apkg apkg_backups/
.sandbox/    то же, для пробных прогонов
Dockerfile  docker-compose.yml  .dockerignore  requirements.txt
```

Структуры данных:
```python
WordRequest(word, custom_example, raw_line)
Entry(word, pos, definition, ipa, examples, sound_url, source)   # source: cambridge | wiktionary
BaseRef(base_word)                                               # словоформа → базовое слово
```

Путь слова: Cambridge → (нет) Wiktionary → (словоформа) снова Cambridge по базовому →
(нет нигде) LLM-подсказка, проверенная по словарю → `problem_words.txt`.

## Команды

```
docker compose run --rm app                боевой прогон (workspace/)
docker compose run --rm app --no-images    без картинок
docker compose run --rm app inspect        разбор output.apkg
docker compose run --rm try                тот же код на .sandbox/
docker compose run --rm test               pytest без сети
docker compose run --rm test -m live       живой смоук (3 слова)
```

## Шаги

### Task 0. Ветка
- [x] `git checkout -b docker-refactor` (незакоммиченные правки переезжают с веткой)

### Task 1. Каркас Docker
- [x] `requirements.txt`: requests, beautifulsoup4, lxml, genanki, fake-useragent, colorama, Pillow, pytest;
      версии зафиксировать после первой успешной сборки на python 3.12
- [x] `Dockerfile` (python:3.12-slim, только зависимости), `.dockerignore`
- [x] `docker-compose.yml`: сервисы `app` / `try` / `test`, `user: "${HOST_UID:-1000}:${HOST_GID:-1000}"`,
      `env_file: .env` (необязательный), код монтируется
- [x] `HOST_UID=757600345`, `HOST_GID=757600345` в `.env`
- [x] `.gitignore`: `workspace/*`, `!workspace/.gitkeep`, `.sandbox/`, `tests/fixtures/cambridge/`,
      `tests/fixtures/wiktionary/`
- [x] allow-лист проекта: `Bash(docker compose run:*)`, `Bash(docker compose build:*)`
- [x] проверка: сборка проходит; файл, созданный из контейнера в `.sandbox/`, принадлежит lipin.evgeniy3;
      из контейнера отвечают Cambridge, Wiktionary, text/image pollinations (по одному запросу)

### Task 2. Фикстуры (до переписывания парсера)
- [x] команда `docker compose run --rm app fixtures` — скачивает список ниже в `tests/fixtures/`
      (нужна и для свежего клона: страницы словарей в git не лежат)
- [x] нет фикстур → тесты **падают** с текстом «запусти fixtures», а не пропускаются
      (пропуск = ноль проверенных единиц с зелёным итогом)
- [x] Cambridge, как пришли, с паузой между запросами: `superficial`, `come-over`, `facilities`,
      `in-the-trenches`, `bailed`, `head-out`, `womb`, `ignight`, `concurrency`
- [x] Wiktionary: `concurrency`, `misspoke`, 404
- [x] LLM: ответ на промпт примеров, ответ на промпт сцен, ответ с пустым `content`
- [x] в `tests/fixtures/README.md` — чем ценен каждый экземпляр

### Task 3. `http.py`, `wordlist.py`
- [x] `fetch`: ретраи, SSL-фолбэк после первой SSLError — в одном месте (сейчас три)
- [x] разбор строк: `word`, `word - пример`, `well-being` не режется, хвост `# …` игнорируется
- [x] `append_unique`; тест на отсутствие дублей
- [x] тесты зелёные, `pytest --collect-only` показывает ненулевое число

### Task 4. `sources/cambridge.py`
- [x] `parse(html)` без сети: три контейнера, словоформа → `BaseRef`, идиома без pos, примеры в два круга,
      `sound_url` вместо скачивания
- [x] тест на каждую из 9 фикстур; ожидаемые значения сверить глазами со страницей

### Task 5. `sources/wiktionary.py`
- [x] REST `/api/rest_v1/page/definition/<word>`: часть речи, первое определение, примеры; HTML-теги снять
- [x] form-of → `BaseRef`; 404 → `None`
- [x] тесты на 3 фикстуры

### Task 6. `llm.py`
- [x] перенос `ask_llm`, `generate_examples`
- [x] `suggest_spelling(word)` + проверка кандидата по словарю (без неё подсказку не писать)
- [x] разобраться, почему в прогоне 09-19 сцены вернулись `0/4`: снять настоящий ответ, диагноз до фикса
- [x] тесты: нумерация, отсев строк без слова, пустой `content`

### Task 7. `images.py`
- [x] перенос `create_image.py` без изменения поведения; временные файлы — в tmp контейнера
- [x] тест коллажа на цветных квадратах: размер, срез водяного знака, 1–4 картинки

### Task 8. `deck.py`
- [x] модель/колода (ID прежние), HTML полей, запись, бэкап старого `output.apkg`
- [x] тест: собрать apkg из двух карточек, вскрыть — 7 полей, ID модели, буллеты, нет битых ссылок на медиа

### Task 9. `pipeline.py`, `cli.py`
- [x] `process()`: цепочка источников, примеры (свой → словарь → LLM до 3), медиа, карточка
- [x] `run`: журналы, бэкап, запись, очистка `words.txt` только в самом конце; `inspect` — из `inspect_apkg.py`
- [x] тесты pipeline с подставными источниками: три исхода, порядок примеров, цепочка Cambridge→Wiktionary→Cambridge
- [x] тесты сохранности: бэкап до перезаписи; падение посреди прогона не чистит `words.txt`;
      свой пример упавшего слова попадает в `problem_words.txt`

### Task 10. Живая проверка в `.sandbox/`
- [x] слова: `bureaucracy` (предметное), `superficial` (абстрактное), `come over` (фразовый), `bailed` (словоформа),
      `concurrency` (только Wiktionary), `misspoke` (Wiktionary → Cambridge `misspeak`), `ignight` (подсказка) —
      все семь путей отработали: 6 карточек, `ignight   # возможно: ignite` в журнале
- [x] `inspect`: битых ссылок 0, звук у 5 из 6 (у `concurrency` его нет — Wiktionary). Найден дефект: у `misspoke`
      2 примера вместо 3 — LLM вернул два предложения одной строкой. Починено (разбивка по предложениям) + тест
- [x] сверка со старым кодом — сделана точнее, чем планировалось: старый `perser_cambrige` и новый `parse`
      на одних и тех же 6 сохранённых страницах, без сети. Нашлось одно расхождение (хвостовой пробел
      в определении) — вернул как было: от него зависит guid заметки
- [x] открыть коллажи глазами: `bureaucracy` по делу (бумаги, формы, здание), `come over` — портреты,
      `superficial` — обнажённая натура (известная болезнь генератора, см. ОБНОВЛЕНИЕ)
- [x] `test -m live` зелёный (5 тестов)

### Task 11. Переезд данных и уборка (Женя: «делай всё до конца»)
- [x] перед переносом посмотреть содержимое; `mv` в `workspace/`: `words.txt`, `success_words.txt`,
      `problem_words.txt`, `apkg_backups/`; сверено: 5/12/12 строк и 12 файлов бэкапов до и после
- [x] удалить `main.py`, `create_image.py`, `inspect_apkg.py`, `data/`, `__pycache__/`
- [x] `README.md` (запуск через Docker), `CLAUDE.md` (новая структура, команды)

### Task 12. Финал
- [x] полный `docker compose run --rm test` — 108 passed; `-m live` — 5 passed
- [x] `grep -n "^- \[ \]"` по этому плану — незакрытого нет
- [x] показать `git status`; коммит — только по команде
- [x] саб-агент-ревьюер (просьба Жени) — критичного нет, находки разобраны ниже

## Ревью (саб-агент, 2026-09-19) — что починено

- свой пример с ` # ` обрезался (`hash - Press the # key…`) → отрезается только маркер `# возможно:`;
- 403 от словаря считался «слова нет» → всё, кроме 200/404, теперь сбой (строка остаётся на ретрай);
- mp3: тело ошибки сохранялось как `word.mp3` → `http.download()` проверяет статус;
- апостроф в слове рвал `<img src='…'>` → `media_name()`; слаг Cambridge `devil-s-advocate` проверен вживую;
- Ctrl+C выбрасывал всю сделанную работу → готовые карточки пишутся, остальное остаётся в `words.txt`;
  колода пишется раньше журналов (нет «успехов» без карточек);
- любой `SSLError` снимал проверку сертификата на весь прогон → только `CERTIFICATE_VERIFY_FAILED`;
- `.env` не был в `.gitignore` (только в локальном exclude) → добавлен; `.sandbox/.gitkeep` теперь попадает в git;
- строка без слова молча исчезала из `words.txt` → остаётся с предупреждением; `write_lines` атомарный; BOM;
- LLM-примеры: формы вроде «came over» отсеивались, дубль словарного примера съедал слот → просим `need+1`,
  буквальные совпадения первыми; `make_collage` обёрнут в try; `init: true`; местное время в контейнере;
- тесты: `http.py` (ретраи, SSL), запись колоды упала, жёсткий крэш, настоящая фикстура Wiktionary с примерами
  (`bail`), слабые проверки усилены. Было 82 теста, стало 108.

Не трогал (осознанно): порядок `a.Ref` раньше определения — как в старом коде, случая в фикстурах нет;
регистр в Wiktionary (`djing` → 404, статья `DJing`) — слово остаётся в `problem_words.txt`.

## Найдено по ходу (не из плана)

- **Чужой звук на карточках — баг старого кода.** Звук искался по всей странице и находил mp3 виджета
  «Word of the Day»: `head out`, `facilities`, `in the trenches` получали произношение слова `misunderstanding`.
  Виджет есть не при каждой загрузке, поэтому раньше не ловилось. Теперь звук ищется только внутри статьи.
  В уже импортированных карточках слов без своей озвучки может стоять чужой mp3.
- **500-е от картинок — лимит апстрима у самого pollinations** (`Per-user limit of 300 RPM exceeded`), не наш код
  и не убранный `model=turbo`. В плохой день слово собирается 3–4 минуты.
- **Запреты для картинок переехали в `negative_prompt`** (за «sana» стоит Stable Diffusion, отрицаний в промпте
  не понимает). Одно парное сравнение на `superficial`: та же сцена и seed — до правки топлес, после — нет.
- **Примеры LLM идут с `reasoning_effort: medium`** — с `low` фразы корявые и склеены в одну строку.

## ОБНОВЛЕНИЕ 2026-09-19 — что вышло иначе, чем в плане

- **uid/gid — в `docker-compose.override.yml`, а не в `.env`.** Чтобы не открывать файл с токеном. Override в git
  не идёт; в общем compose остался дефолт `${HOST_UID:-1000}`.
- **Фикстуры качает отдельный сервис:** `docker compose run --rm fixtures` (не `app fixtures`) — скачивание
  тестовых данных не должно жить в боевом пакете.
- **Добавлен `models.py`** (структуры данных) и `inspect_apkg.py` внутри пакета.
- **«Сцены от LLM: 0/4» — причина найдена и воспроизведена.** Модель `gpt-oss-20b` без `reasoning_effort` тратит
  на размышления весь лимит ответа (1500 токенов) и отдаёт пустой `content`: `come over` → 1500 токенов, 0 сцен;
  с `low` → 145 токенов, 4 сцены. Фикс: сцены идут с `medium` (связнее), повтор на пустой ответ — с `low`;
  примеры и опечатки — сразу `low`. Настоящий пустой ответ по заказу не снимается (недетерминирован) — в тесте
  он собран из настоящего `scenes.json` заменой `content`.
- **В промпт сцен добавлен запрет рисовать слово буквами:** для `enraged` и `superficial` первой сценой выходила
  надпись неоном.
- **Токен pollinations на текстовом эндпоинте не распознаётся:** `user_tier: anonymous` с токеном и без.
- **Мелкие улучшения поведения:** 5xx/429 словаря теперь сбой (строка остаётся в `words.txt`), а не «слова нет»;
  неожиданная ошибка на одном слове не роняет весь список; если не собрано ни одной карточки — `output.apkg`
  не перезаписывается; `model=turbo` из URL картинки убран (игнорировался).

## Предположения и риски

- Cambridge из контейнера ответил 200 с проверкой SSL — проверено один раз 2026-09-19, состояние VPN
  неизвестно. SSL-фолбэк поэтому остаётся. Pollinations из контейнера не проверялся (Task 1).
- Нечёткий поиск Wiktionary для опечаток не годится: верно 1 из 4 (`ignight`→`ignite`; `marmaid`, `incanny`,
  `compregend` — мимо). Подсказки — от LLM, словарь только подтверждает, что слово существует.
- `words.txt` и `problem_words.txt` сейчас в git; после переезда в `workspace/` git покажет их удалёнными —
  это ожидаемо (личные данные не должны лежать в публичном репо).
- Фикстуры LLM-ответов (наш запрос, наш ответ) в git идут; страницы Cambridge и Wiktionary — нет.

## Вне этого плана

- Другой генератор картинок (sana плохо рисует абстрактные слова — промптом не лечится).
- AnkiConnect, восстановление 265 удалённых карточек.
