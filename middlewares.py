import os
import shutil
import time
import threading
from functools import wraps
from flask import request, g, jsonify
from webwhatsapi import WhatsAPIDriver, WhatsAPIDriverStatus
from werkzeug.utils import secure_filename
from settings import (
    CHROME_CACHE_PATH,
    CHROME_IS_HEADLESS,
    CHROME_DISABLE_SANDBOX,
    CHROME_WINDOW_SIZE,
    CHROME_DISABLE_GPU,

    ALLOWED_EXTENSIONS,
    STATIC_FILES_PATH
)
from handlers import RepeatedTimer
from routes import HandleReceivedMessage

drivers = dict()
timers = dict()
semaphores = dict()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.driver_status != WhatsAPIDriverStatus.LoggedIn:
            return jsonify({"error": "client is not logged in"})
        return f(*args, **kwargs)
    return decorated_function

def init_driver(client_id):
    profile_path = CHROME_CACHE_PATH + str(client_id)
    if not os.path.exists(profile_path):
        os.makedirs(profile_path)
    
    chrome_options = [
        'window-size=' + CHROME_WINDOW_SIZE,
        '--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/60.0.3112.78 Chrome/60.0.3112.78 Safari/537.36'
    ]
    if CHROME_IS_HEADLESS:
        chrome_options.append('--headless')
    if CHROME_DISABLE_SANDBOX:
        chrome_options.append('--no-sandbox')
    if CHROME_DISABLE_GPU:
        chrome_options.append('--disable-gpu')
    
    d = WhatsAPIDriver(
        username=client_id, 
        profile=profile_path, 
        client='chrome', 
        chrome_options=chrome_options
    )
    return d


def init_client(client_id):
    """Initialse a driver for client and store for future reference
    
    @param client_id: ID of client user
    @return whebwhatsapi object
    """
    if client_id not in drivers:
        drivers[client_id] = init_driver(client_id)
    return drivers[client_id]


def delete_client(client_id, remove_cache):
    if client_id in drivers:
        drivers.pop(client_id).quit()
        try:
            timers[client_id].stop()
            timers[client_id] = None
            release_semaphore(client_id)
            semaphores[client_id] = None
        except:
            pass

    if remove_cache:
        pth = CHROME_CACHE_PATH + g.client_id
        shutil.rmtree(pth)


def init_timer(client_id):
    if client_id in timers and timers[client_id]:
        timers[client_id].start()
        return
    timers[client_id] = RepeatedTimer(2, check_new_messages, client_id)


def check_new_messages(client_id):
    if client_id not in drivers or not drivers[client_id] or not drivers[client_id].is_logged_in():
        timers[client_id].stop()
        return

    if not acquire_semaphore(client_id, True):
        return

    try:
        res = drivers[client_id].get_unread()
        for message_group in res:
            message_group.chat.send_seen()
        # Release thread lock
        release_semaphore(client_id)
        # If we have new messages, do something with it
        if res:
            HandleReceivedMessage(drivers[client_id], res, client_id).start()
    except:
        pass
    finally:
        # Release lock anyway, safekeeping
        release_semaphore(client_id)

def get_client_info(client_id):
    if client_id not in drivers:
        return None

    driver_status = drivers[client_id].get_status()
    is_alive = False
    is_logged_in = False
    if (driver_status == WhatsAPIDriverStatus.NotLoggedIn
        or driver_status == WhatsAPIDriverStatus.LoggedIn):
        is_alive = True
    if driver_status == WhatsAPIDriverStatus.LoggedIn:
        is_logged_in = True
    
    return {
        "is_alive": is_alive,
        "is_logged_in": is_logged_in,
        "is_timer": bool(timers[client_id]) and timers[client_id].is_running
    }


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def send_media(chat_id, requestObj):
    files = requestObj.files
    if not files:
        return jsonify({'Status': False})

    # create user folder if not exists
    profile_path = create_static_profile_path(g.client_id)

    file_paths = []
    for file in files:
        file = files.get(file)
        if file.filename == '':
            return {'Status': False}

        if not file or not allowed_file(file.filename):
            return {'Status': False}

        filename = secure_filename(file.filename)

        # save file
        file_path = os.path.join(profile_path, filename)
        file.save(file_path)
        file_path = os.path.join(os.getcwd(), file_path)

        file_paths.append(file_path)

    caption = requestObj.form.get('message')

    res = None
    for file_path in file_paths:
        res = g.driver.send_media(file_path, chat_id, caption)
    return res


def create_static_profile_path(client_id):
    profile_path = os.path.join(STATIC_FILES_PATH, str(client_id))
    if not os.path.exists(profile_path):
        os.makedirs(profile_path)
    return profile_path


def acquire_semaphore(client_id, cancel_if_locked=False):
    if not client_id:
        return False

    if client_id not in semaphores:
        semaphores[client_id] = threading.Semaphore()

    timeout = 10
    if cancel_if_locked:
        timeout = 0

    val = semaphores[client_id].acquire(blocking=True, timeout=timeout)

    return val

def release_semaphore(client_id):
    if not client_id:
        return False

    if client_id in semaphores and not semaphores[client_id] is None:
        semaphores[client_id].release()
