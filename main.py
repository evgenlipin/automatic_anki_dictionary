import requests
from bs4 import BeautifulSoup
import genanki
import os
from clean import clean_all
from create_image import create_image_collage

def clean_words_txt():
    with open("words.txt", 'w', encoding='utf-8') as wfile:
        wfile.write('')

def get_sound_word(sound_url, word, headers):
    response_sound = requests.get(sound_url, headers=headers)
    with open(word + '.mp3', 'wb') as f:
        f.write(response_sound.content)

def perser_cambrige(headers, base_url, dictionary_url, word):
    print('The word "' + word + '" is loaded...')
    word_url = dictionary_url + word
    response_word = requests.get(word_url, headers=headers)
    soup = BeautifulSoup(response_word.text, "lxml") #html.parser
    data = soup.find("div", class_ = 'pr entry-body__el')
    
    type_word = data.find("span", class_ = "pos dpos").text
    definition = data.find("div", class_ = "def ddef_d db").text[:-2]
    example_sentence = data.find("span", class_ = "eg deg").text
    pronanciation = data.find("span", class_ = "ipa dipa lpr-2 lpl-1").text 
    sound_url = base_url + data.find("source", type = "audio/mpeg")['src']

    get_sound_word(sound_url, word, headers)

    return type_word, definition, example_sentence, pronanciation

def main():
    base_url = 'https://dictionary.cambridge.org'
    dictionary_url = 'https://dictionary.cambridge.org/us/dictionary/english/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0;Win64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
    }

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
        'qfmt': "<div style='font-family: Arial; font-size: 60px;color:#FF80DD;'>{{word}}</div><hr>{{sound}}<hr><div style='font-family: Arial; font-size: 25px;color:#79005E;'>{{type}}</div><div style='font-family: Arial; font-size: 25px;color:#AB2B52;'>{{ipa}}</div>",
        'afmt': "<hr id=answer><div style='font-family: Arial; color:#FF80DD;'>{{FrontSide}}</div><hr><div  style='font-family: Arial; color:#00aaaa; text-align:left;'>Meaning: {{meaning}}</div><hr><div  style='font-family: Arial; color:#9CFFFA; text-align:left;'>&nbsp;→&nbsp;Example: {{example}}</div><hr>{{pic}}",
        },
    ], css= '.card {font-family: arial; font-size: 20px; text-align: center; color: black; background-color: white;}')

    my_deck = genanki.Deck(
    1686686578,
    'automatic_dictionary')
    
    my_package = genanki.Package(my_deck)    
    problem_words = []

    if os.path.exists('words.txt') == False:
        print('"words.txt" does not exist') 
    elif os.stat('words.txt').st_size == 0:
        print('"words.txt" list is empty')
    else:
        with open('words.txt', 'r', encoding='utf-8') as rfile:
            lines = [line.strip().strip('*-.,<>}{!@#$%^&()').lower() for line in rfile.readlines() if line.strip()]
        for word in lines:
            if word:
                try:
                    type_word, definition, example_sentence, pronanciation = perser_cambrige(headers, base_url, dictionary_url, word)
                except AttributeError:
                    problem_words.append(word)
                    print("Parsing Error\n")
                    continue

                if create_image_collage(word=word, headers=headers) == False:
                    problem_words.append(word)
                    print("Image Error\n")
                    continue                    

                my_note = genanki.Note(
                model=my_model,
                fields=[word, type_word, pronanciation, definition, example_sentence, "[sound:" + word + ".mp3]", "<img src='collage_" + word + ".jpg'>"])
                
                my_deck.add_note(my_note)
                my_package.media_files.append(word + '.mp3')
                my_package.media_files.append('collage_' + word + '.jpg')
                print("Success\n")

        if problem_words:
            with open('problem_words.txt', 'a', encoding='utf-8') as afile:
                for word in problem_words:
                    afile.write(word + "\n")
                print('Creat "problem_words.txt"\n')
        else:
            print("Problem words did't find")

        my_package.write_to_file('output.apkg')
        clean_words_txt()
        clean_all()
        print("The program is finished")
    
if __name__ == "__main__":
    main()

