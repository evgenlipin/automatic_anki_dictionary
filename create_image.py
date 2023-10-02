from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
import shutil
from PIL import Image, UnidentifiedImageError
import os

root_dir_images = os.getcwd() + '/images'

def get_images_from_istockphoto(word, headers):
    base_pic_url = "https://www.istockphoto.com/ru/search/2/image?phrase="
    url_encoded_string = quote(word)
    pic_full_url = base_pic_url + url_encoded_string

    response_pic = requests.get(pic_full_url, headers=headers)
    soup = BeautifulSoup(response_pic.text, "lxml") #html.parser
    data = soup.find("div", class_ = 'DE6jTiCmOG8IPNVbM7pJ').find_all('img')

    image_urls = [image['src'] for image in data]

    if not os.path.exists(root_dir_images):
        os.makedirs(root_dir_images)

    count = 0
    for image_url in image_urls[:8:2]:
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

def create_image_collage(word, headers):
    get_images_from_istockphoto(word, headers)
    try:
        create_collage(word)
    except UnidentifiedImageError:
        delete_images(word)
        return False
    
    delete_images(word)
    return True

if __name__ == "__main__":
    create_image_collage()