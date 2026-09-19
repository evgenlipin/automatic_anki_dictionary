[English version](#automatic-anki-dictionary-) | [Русская версия](#автоматический-словарь-anki-)

# Automatic Anki Dictionary 📚

Builds an Anki deck (`output.apkg`) from a list of English words. For each word it takes the part of speech,
definition, IPA, examples and pronunciation from the Cambridge Dictionary (falling back to Wiktionary for words
Cambridge doesn't have), tops the examples up to three with an LLM, and adds a collage of four generated images.

## How to Run 🚀

Requires Docker.

1. `git clone [repository URL]` and `cd` into it.
2. Put your words into `workspace/words.txt`, one per line. Your own example sentence goes after ` - `:
   ```
   superficial
   arrogant - I watched the interview and felt he came over as quite arrogant.
   ```
3. `docker compose run --rm app` — the deck appears in `workspace/output.apkg`; import it into Anki.

| Command | What it does |
|---|---|
| `docker compose run --rm app` | build the deck from `workspace/words.txt` |
| `docker compose run --rm app --no-images` | same, without image collages (much faster) |
| `docker compose run --rm app inspect` | show what is inside `workspace/output.apkg` |
| `docker compose run --rm try` | same as `app`, but on `.sandbox/` — for experiments |
| `docker compose run --rm fixtures` | download dictionary pages for the tests (not stored in git) |
| `docker compose run --rm test` | run the tests (no network) |
| `docker compose run --rm test -m live` | smoke test against the real dictionaries |

After a run:
- `workspace/success_words.txt` — words that became cards, `workspace/problem_words.txt` — words not found in any
  dictionary (with a `# возможно: …` hint if it looks like a typo). Lines keep the `words.txt` format and can be
  pasted back as is.
- words that failed because of the network stay in `words.txt` for the next run; Ctrl+C keeps the cards that are
  already done and leaves the rest in `words.txt`;
- the previous `output.apkg` is copied to `workspace/apkg_backups/` before being overwritten.

Optional: `POLLINATIONS_TOKEN=...` in `.env` (pollinations.ai). If files in `workspace/` end up owned by another
user, set your uid/gid: `HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose run --rm app`.

# Автоматический словарь Anki 📚

Собирает колоду Anki (`output.apkg`) из списка английских слов. Для каждого слова берёт часть речи, определение,
транскрипцию, примеры и озвучку из Cambridge Dictionary (а для слов, которых там нет, — из Wiktionary), добирает
примеры до трёх через LLM и добавляет коллаж из четырёх сгенерированных картинок.

## Как запустить 🚀

Нужен Docker.

1. `git clone [URL репозитория]` и перейти в папку.
2. Записать слова в `workspace/words.txt`, по одному на строку. Свой пример — после ` - `:
   ```
   superficial
   arrogant - I watched the interview and felt he came over as quite arrogant.
   ```
3. `docker compose run --rm app` — колода появится в `workspace/output.apkg`, её нужно импортировать в Anki.

| Команда | Что делает |
|---|---|
| `docker compose run --rm app` | собрать колоду из `workspace/words.txt` |
| `docker compose run --rm app --no-images` | то же без коллажей (намного быстрее) |
| `docker compose run --rm app inspect` | показать, что лежит в `workspace/output.apkg` |
| `docker compose run --rm try` | то же, что `app`, но на `.sandbox/` — для экспериментов |
| `docker compose run --rm fixtures` | скачать страницы словарей для тестов (в git не лежат) |
| `docker compose run --rm test` | тесты (без сети) |
| `docker compose run --rm test -m live` | смоук-тест на настоящих словарях |

После прогона:
- `workspace/success_words.txt` — слова, ставшие карточками; `workspace/problem_words.txt` — слова, которых нет ни в
  одном словаре (с подсказкой `# возможно: …`, если это похоже на опечатку). Строки в формате `words.txt` — их
  можно вернуть во вход как есть;
- слова, упавшие из-за сети, остаются в `words.txt` до следующего прогона; Ctrl+C сохраняет уже готовые карточки,
  остальное остаётся в `words.txt`;
- предыдущий `output.apkg` перед перезаписью копируется в `workspace/apkg_backups/`.

Необязательно: `POLLINATIONS_TOKEN=...` в `.env` (pollinations.ai). Если файлы в `workspace/` создаются от чужого
пользователя — задать свои uid/gid: `HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose run --rm app`.
