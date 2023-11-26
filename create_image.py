from PIL import Image
import os
import freeGPT
from io import BytesIO
from asyncio import run, gather
import shutil
root_dir_images = f'{os.getcwd()}/data/images'


# asynchronous function for creating and saving image generation
async def get_images(prompt, file_name):
    try:
        resp = await getattr(freeGPT, "prodia").Generation().create(prompt)
        with Image.open(BytesIO(resp)) as image:
            image.save(f'{file_name}.png')
    except Exception as e:
        print(f"Generation Image Error: {e}\n")

# asynchronous function for creating list of commands
async def get_images_prodia(word, definition, example_sentence): 
    prompts = [
        f'{word} - {definition}',
        f'{example_sentence}',
        f'A scene describing the word "{word}" which means {definition}',
        f'Representation of the word "{word}" which means {definition}'
    ]

    if not os.path.exists(root_dir_images):
        os.makedirs(root_dir_images)

    tasks = []
    for i, prompt in enumerate(prompts, 1):
        file_name = f'{root_dir_images}/{word}{str(i)}'
        tasks.append(get_images(prompt, file_name))
    
    await gather(*tasks)

# creating collage from 4 gereratic pictures
def create_collage(root_dir_data,word):
    collage = Image.new('RGB', (1600, 400))
    positions_images = [(0,0),(400,0),(800,0),(1200,0)]
    for i in range(1,5):
        image_original = Image.open(f'{root_dir_images}/{word}{str(i)}.png')
        width, height = image_original.size
        new_width = 400
        new_height = int(400 * height / width)
        image_resize = image_original.resize((new_width, new_height))
        collage.paste(image_resize, positions_images[i-1])
    collage.save(f'{root_dir_data}/collage_{word}.jpg')

def create_image_collage(root_dir_data, word, definition, example_sentence):
    run(get_images_prodia(word, definition, example_sentence))
    create_collage(root_dir_data, word)
    shutil.rmtree(root_dir_images)
