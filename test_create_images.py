from create_image import get_images_from_istockphoto
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0;Win64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
}

def main(word, headers):
    get_images_from_istockphoto(word, headers)

if __name__ == "__main__":
    main(word="though", headers=headers)