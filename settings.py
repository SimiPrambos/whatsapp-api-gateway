import os, sys, logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

DATABASE_URI = "sqlite:///{}".format(os.path.join(BASE_DIR, "apiwahstapp.db"))

ALLOWED_EXTENSIONS = ('avi', 'mp4', 'png', 'jpg', 'jpeg', 'gif', 'mp3', 'doc', 'docx', 'pdf')

STATIC_FILES_PATH = 'static/'

CHROME_IS_HEADLESS = False
CHROME_DISABLE_SANDBOX = True
CHROME_CACHE_PATH = BASE_DIR + '/chrome_cache/'
CHROME_DISABLE_GPU = True
CHROME_WINDOW_SIZE = "910,512"