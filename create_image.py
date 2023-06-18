from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
import shutil
from icrawler.builtin import GoogleImageCrawler
from PIL import Image
import os

root_dir_images = os.getcwd() + '/images'

def get_images_from_google(word):
    google_crawler = GoogleImageCrawler(storage={'root_dir': root_dir_images})

    filters = {

        'size': 'medium',
        'type': 'photo',
        'license': 'commercial,modify'
    }
    google_crawler.crawl(word, filters=filters, max_num=2)

def convert_png_to_jpg():
    files = os.listdir(root_dir_images)
    for file in files:
        if file.endswith('.png'):
            image = Image.open(root_dir_images + '/' + file)        
            image = image.convert('RGB')
            image.save(root_dir_images + '/' + file[:6] + '.jpg')

def rename_jpg(word):
    count = 1
    files = os.listdir(root_dir_images)
    for file in files:
        if file.endswith('.jpg'):
            os.rename(os.path.join(root_dir_images, file), os.path.join(root_dir_images, word + str(count) + '.jpg'))
            count += 1
            
def get_images_from_stock(word, headers):
    base_pic_url = "https://www.istockphoto.com/ru/search/2/image?phrase="
    url_encoded_string = quote(word)
    pic_full_url = base_pic_url + url_encoded_string

    response_pic = requests.get(pic_full_url, headers=headers)
    soup = BeautifulSoup(response_pic.text, "lxml") #html.parser
    data = soup.find("div", class_ = 'DE6jTiCmOG8IPNVbM7pJ').find_all('img')

    image_urls = [image['src'] for image in data]

    count = 2
    for image_url in image_urls[:2]:
        count += 1
        response = requests.get(image_url, stream=True)
        with open(root_dir_images+ '/' + word + str(count) + '.jpg', 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)

def create_collage(word):
    collage = Image.new('RGB', (1600, 400))
    positions_images = [(0,0),(400,0),(800,0),(1200,0)]
    for i in range(1,5):
        image_original = Image.open(root_dir_images + '/' + word + str(i) + '.jpg')
        width, height = image_original.size
        new_width = 400
        new_height = int(400 * height / width)
        image_resize = image_original.resize((new_width, new_height))
        collage.paste(image_resize, positions_images[i-1])
    collage.save('collage_' + word + '.jpg')

def delete_images(word):
    files = os.listdir(root_dir_images)
    for file in files:
        if (file.endswith('.jpg')) or (file.endswith('.png')):
            os.remove(os.path.join(root_dir_images, file))
    os.removedirs(root_dir_images)

def delete_collages():
    files = os.listdir(os.getcwd())
    for file in files:
        if file.endswith('.jpg'):
            os.remove(os.path.join(os.getcwd(), file))
    
def create_image_collage(word, headers):
    get_images_from_google(word)
    convert_png_to_jpg()
    rename_jpg(word)
    get_images_from_stock(word, headers)
    create_collage(word)
    delete_images(word)

if __name__ == "__main__":
    create_image_collage()