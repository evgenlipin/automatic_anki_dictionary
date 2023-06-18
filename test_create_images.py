from create_image import get_images_from_google, get_images_from_stock,rename_jpg, convert_png_to_jpg, create_collage, delete_images

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0;Win64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
}

def main(word, headers):
    get_images_from_google(word)
    convert_png_to_jpg()
    rename_jpg(word)
    get_images_from_stock(word, headers)
    create_collage(word)
    delete_images(word)
    
if __name__ == "__main__":
    with open('words.txt', 'r', encoding='utf-8') as rfile:
        lines = [line.strip() for line in rfile.readlines()]

    for word in lines:
        main(word=word, headers=headers)