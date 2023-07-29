import os

def delete_collages():
    files = os.listdir(os.getcwd())
    for file in files:
        if file.endswith('.jpg'):
            os.remove(os.path.join(os.getcwd(), file))

def delete_soundfile():
    files = os.listdir(os.getcwd())
    for file in files:
        if (file.endswith('.mp3')):
            os.remove(os.path.join(os.getcwd(), file))

def clean_all():
    delete_soundfile()
    delete_collages()

if __name__ == "__main__":
    clean_all()