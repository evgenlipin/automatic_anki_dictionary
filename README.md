[English version](#automatic-anki-dictionary-) | [Русская версия](#автоматический-словарь-anki-)

# Automatic Anki Dictionary 📚

This program allows you to create sets of Anki flashcards from a list of words. It uses the `requests` and `BeautifulSoup` libraries to extract data about words from the Cambridge dictionary website, and then uses the `genanki` library to create Anki flashcards with this information. The program also creates a collage of four suitable images for each word.

## How to Run 🚀

1. Clone the repository using the command `git clone [repository URL]`.
2. Create a virtual environment in repository folder(optional but recommended for isolation) `python3 -m venv venv` and `source venv/bin/activate`.
3. Install the required libraries by running the command `pip install -r requirements.txt`.
4. Add the words you want to include in the set of flashcards to the words.txt file, one word per line.
5. Run the program using the command `python main.py`.
6. The program will create an `.apkg` file with a set of Anki flashcards that can be imported into the Anki application.

If the program is unable to create a flashcard for a particular word, it will add that word to the `problem_words.txt` file.

## Requirements

# Автоматический словарь Anki 📚

Эта программа позволяет создавать наборы карточек Anki из списка слов. Она использует библиотеки `requests` и `BeautifulSoup` для извлечения данных о словах с сайта словаря Кембриджа, а затем использует библиотеку `genanki` для создания карточек Anki с этой информацией. Программа также создает коллаж из четырех подходящих картинок для каждого слова.

## Как запустить 🚀

1. Скопируйте репозиторий с помощью команды `git clone [URL репозитория]`.
2. Создайте виртуальное окружение в папке репозитория(по желанию, но рекомендуется для изоляции) `python3 -m venv venv` and `source venv/bin/activate`.
3. Установите необходимые библиотеки, выполнив команду `pip install -r requirements.txt`.
4. Добавьте построчно в файл `words.txt` слова, которые вы хотите добавить в набор карточек.
5. Запустите программу с помощью команды `python main.py`.
6. Программа создаст файл `.apkg` с набором карточек Anki, который можно импортировать в приложение Anki.

Если программа не смогла создать карточку для какого-то слова, она добавит это слово в файл `problem_words.txt`.
