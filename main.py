import requests
from bs4 import BeautifulSoup
import genanki
import os
from create_image import create_image_collage
import random
import shutil

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0;Win64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
}
root_dir_data = f'{os.getcwd()}/data'

# cleaning "words.txt"
def clean_words_txt():
    with open("words.txt", 'w', encoding='utf-8') as wfile:
        wfile.write('')

# saving soundfile
def get_sound_word(sound_url, word):
    response_sound = requests.get(sound_url, headers=headers)
    with open(f'{root_dir_data}/{word}.mp3', 'wb') as f:
        f.write(response_sound.content)
    
# parsing examles from reverso.net
def parser_reverso(word):
    word_url = f'https://context.reverso.net/translation/english-russian/{word}'
    response_word = requests.get(word_url, headers=headers)
    soup = BeautifulSoup(response_word.text, "lxml") #html.parser
    examples = soup.find_all('div', class_='src ltr')
    list_exaples = [] 
    for example in examples:
        example_sentence = example.text.strip()
        list_exaples.append(example_sentence)
    return random.choice(list_exaples)

# parsing data of word from cambridge.org
def perser_cambrige(word):
    word_url = f'https://dictionary.cambridge.org/us/dictionary/english/{word}'
    response_word = requests.get(word_url, headers=headers)
    soup = BeautifulSoup(response_word.text, "lxml") #html.parser
    data = soup.find("div", class_ = 'pr entry-body__el')
    
    type_word = data.find("span", class_ = "pos dpos").text
    definition = data.find("div", class_ = "def ddef_d db").text
    try:
        example_sentence = data.find("span", class_ = "eg deg").text
    except AttributeError:
        example_sentence = parser_reverso(word)
    pronanciation = data.find("span", class_ = "ipa dipa lpr-2 lpl-1").text 
    sound_url = 'https://dictionary.cambridge.org/' + data.find("source", type = "audio/mpeg")['src']

    get_sound_word(sound_url, word)

    return type_word, definition, example_sentence, pronanciation

def process_word(word):
    print(f'The word "{word}" is loading...')
    try:
        type_word, definition, example_sentence, pronanciation = perser_cambrige(word)
    except AttributeError as e:
        return None

    create_image_collage(root_dir_data, word, definition, example_sentence)
    
    return type_word, definition, example_sentence, pronanciation

def main():

    my_model = genanki.Model(
    1686681943,
    'Basic',
    fields=[
        {'name': 'word'},
        {'name': 'type'},
        {'name': 'ipa'},
        {'name': 'meaning'},
        {'name': 'example'},
        {'name': 'sound'},
        {'name': 'pic'},
    ],
    templates=[
        {
        'name': 'Card 1',
        'qfmt': "<div style='font-family: Arial; font-size: 60px;color:#FF80DD;'>{{word}}{{sound}}</div><hr><div style='font-family: Arial; font-size: 25px;color:#79005E;'>{{type}}</div><div style='font-family: Arial; font-size: 25px;color:#AB2B52;'>{{ipa}}</div>",
        'afmt': "<div id=answer style='font-family: Arial; color:#FF80DD;'>{{FrontSide}}</div><hr><div  style='font-family: Arial; color:#00aaaa; text-align:left;'>Meaning: {{meaning}}</div><hr><div  style='font-family: Arial; color:#9CFFFA; text-align:left;'>&nbsp;→&nbsp;Example: {{example}}</div><hr>{{pic}}",
        },
    ], css= '.card {font-family: arial; font-size: 20px; text-align: center; color: black; background-color: black;}')

    my_deck = genanki.Deck(
    1686686578,
    'automatic_dictionary')
    
    my_package = genanki.Package(my_deck)    
    problem_words = []

    if os.path.exists('words.txt') == False:
        print("'words.txt' doen't exist") 
    elif os.stat('words.txt').st_size == 0:
        print('"words.txt" list is empty')
    else:
        with open('words.txt', 'r', encoding='utf-8') as rfile:
            lines = [line.strip().strip('*-.,<>}{!@#$%^&()').lower() for line in rfile.readlines() if line.strip()]
        for word in lines:
            if word:
                try:
                    if not os.path.exists(root_dir_data):
                        os.makedirs(root_dir_data)

                    type_word, definition, example_sentence, pronanciation = process_word(word)
                    print("Success\n")
                except TypeError as e:
                    print(f"Processing Error\n")
                    problem_words.append(word)
                    continue

                my_note = genanki.Note(
                model=my_model,
                fields=[word, type_word, pronanciation, definition, example_sentence, f"[sound:{word}.mp3]", f"<img src='collage_{word}.jpg'>"])
                
                my_deck.add_note(my_note)
                my_package.media_files.append(f'{root_dir_data}/{word}.mp3')
                my_package.media_files.append(f'{root_dir_data}/collage_{word}.jpg')

        if problem_words:
            with open('problem_words.txt', 'a', encoding='utf-8') as afile:
                for word in problem_words:
                    afile.write(f"{word}\n")
                print('Creat "problem_words.txt"\n')
        else:
            print("Problem words did't find")

        my_package.write_to_file('output.apkg')
        clean_words_txt()
        shutil.rmtree(root_dir_data)
        print("The program is finished")
    
if __name__ == "__main__":
    main()