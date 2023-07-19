import requests
from bs4 import BeautifulSoup
import genanki
import os
from create_image import create_image_collage, delete_collages

def clean_words_txt():
    with open("words.txt", 'w', encoding='utf-8') as wfile:
        wfile.write('')

def delete_soundfile():
    files = os.listdir(os.getcwd())
    for file in files:
        if (file.endswith('.mp3')):
            os.remove(os.path.join(os.getcwd(), file))

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
    
    with open('words.txt', 'r', encoding='utf-8') as rfile:
        lines = [line.strip().strip('*').lower() for line in rfile.readlines() if line.strip()]

    for word in lines:
        print("The word '" + word + "' is loaded...")
        word_url = dictionary_url + word
        response_word = requests.get(word_url, headers=headers)
        soup = BeautifulSoup(response_word.text, "lxml") #html.parser
        data = soup.find("div", class_ = 'pr entry-body__el')
        
        type_word = data.find("span", class_ = "pos dpos").text
        definition = data.find("div", class_ = "def ddef_d db").text[:-2]
        example_sentence = data.find("span", class_ = "eg deg").text
        pronanciation = data.find("span", class_ = "ipa dipa lpr-2 lpl-1").text 
        sound_url = base_url + data.find("source", type = "audio/mpeg")['src']

        response_sound = requests.get(sound_url, headers=headers)
        with open(word + '.mp3', 'wb') as f:
            f.write(response_sound.content)

        create_image_collage(word=word, headers=headers)

        my_note = genanki.Note(
        model=my_model,
        fields=[word, type_word, pronanciation, definition, example_sentence, "[sound:" + word + ".mp3]", "<img src='collage_" + word + ".jpg'>"])

        my_deck.add_note(my_note)
        my_package.media_files.append(word + '.mp3')
        my_package.media_files.append('collage_' + word + '.jpg')

    my_package.write_to_file('output.apkg')
    clean_words_txt()
    delete_soundfile()
    delete_collages()
    print("The program is finished")
    
if __name__ == "__main__":
    main()

