import os, sys, logging, base64
from logging.handlers import TimedRotatingFileHandler
import werkzeug
from flask import Flask, request, abort, g, jsonify, send_file
from webwhatsapi import WhatsAPIDriver, WhatsAPIDriverStatus
from selenium.common.exceptions import WebDriverException
from settings import STATIC_FILES_PATH, DATABASE_URI, BASE_DIR
from middlewares import (
    drivers,
    acquire_semaphore,
    init_client,
    init_driver,
    init_timer,
    release_semaphore,
    login_required,
    get_client_info
)
from handlers import WhatsAPIJSONEncoder
from routes import HandleSendMessage
from models import db, ApiConfig

app = Flask(__name__)
app.json_encoder = WhatsAPIJSONEncoder
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
db.init_app(app)

logger = None
log_file = 'log.txt'
log_level = logging.INFO

def get_data(client_id):
    with app.app_context():
        return ApiConfig.query.filter_by(client=client_id).first()

def save_file(b64_string, filename):
    filepath = BASE_DIR+"/media/"+filename
    with open(filepath, "wb") as rfile:
        rfile.write(base64.b64decode(b64_string.split(',')[1]))
        rfile.close()
    if os.path.exists(filepath):
        return filepath
    else:
        return False

def create_logger():
    global logger

    formatter = logging.Formatter('%(asctime)s|%(levelname)s|%(message)s')
    handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1)
    handler.setFormatter(formatter)
    handler.setLevel(log_level)
    handler.suffix = "%Y-%m-%d"
    logger = logging.getLogger("sacplus")
    logger.setLevel(log_level)
    logger.addHandler(handler)

@app.before_request
def before_request():
    global logger
    
    if not request.url_rule:
        abort(404)

    if logger == None:
        create_logger()
    logger.info("API call " + request.method + " " + request.url)

    auth_key = request.args.get('token')
    g.client_id = 'admin'
    rule_parent = request.url_rule.rule.split('/')[1]
    
    conf = ApiConfig.query.filter_by(client=g.client_id).first()
    API_KEY = conf.key

    if API_KEY and auth_key != API_KEY:
        abort(401, 'you must send valid token')
        raise Exception()

    if not g.client_id and rule_parent != 'admin':
        abort(400, 'client ID is mandatory')

    acquire_semaphore(g.client_id)

    # Create a driver object if not exist for client requests.
    if rule_parent != 'admin':
        if g.client_id not in drivers:
            drivers[g.client_id] = init_client(g.client_id)
        
        g.driver = drivers[g.client_id]
        g.driver_status = WhatsAPIDriverStatus.Unknown
        
        if g.driver is not None:
            g.driver_status = g.driver.get_status()
        
        # If driver status is unkown, means driver has closed somehow, reopen it
        if (g.driver_status != WhatsAPIDriverStatus.NotLoggedIn
            and g.driver_status != WhatsAPIDriverStatus.LoggedIn):
            drivers[g.client_id] = init_client(g.client_id)
            g.driver_status = g.driver.get_status()
        
        init_timer(g.client_id)


@app.after_request
def after_request(r):
    """This runs after every request end. Purpose is to release the lock acquired
    during staring of API request"""
    if 'client_id' in g and g.client_id:
        release_semaphore(g.client_id)
    return r


# -------------------------- ERROR HANDLER -----------------------------------

@app.errorhandler(werkzeug.exceptions.InternalServerError)
def on_bad_internal_server_error(e):
    if 'client_id' in g and g.client_id:
        release_semaphore(g.client_id)
    if type(e) is WebDriverException and 'chrome not reachable' in e.msg:
        drivers[g.client_id] = init_driver(g.client_id)
        return jsonify({'success': False,
                        'message': 'For some reason, browser for client ' + g.client_id + ' has closed. Please, try get QrCode again'})
    else:
        raise e


'''
#####################
##### API ROUTES ####
#####################
'''
# ---------------------------- WhatsApp ----------------------------------------

@app.route('/screen', methods=['GET'])
def get_screen():
    img_title = 'screen_' + g.client_id + '.png'
    image_path = STATIC_FILES_PATH + img_title
    if g.driver_status != WhatsAPIDriverStatus.LoggedIn:
        try:
            g.driver.get_qr(image_path)
            return send_file(image_path, mimetype='image/png')
        except Exception as err:
            pass
    g.driver.screenshot(image_path)
    return send_file(image_path, mimetype='image/png')

@app.route('/chats', methods=['POST'])
@login_required
def send_message():
    args = request.get_json()
    if not args:
        abort(401, 'payload is required!')
    HandleSendMessage(g.driver, args['recipient'], args['content']).start()
    return jsonify({"status":True})
    
@app.route('/sendfile', methods=['POST'])
@login_required
def send_message_file():
    args = request.get_json()
    if not args:
        abort(401, 'payload is required!')
    saved_file = save_file(args['media'], args['filename'])
    if saved_file:
        recipient = args['recipient']+'@c.us' if not '@c.us' in args['recipient'] else args['recipient']
        g.driver.send_media(saved_file, args['recipient'], args['content'])
        return jsonify({"status":True})
    else:
        return jsonify({"status":False})

@app.route('/info', methods=['GET'])
def get_info():
    data = ApiConfig.query.filter_by(client=g.client_id).first()
    return jsonify(dict(
        client=data.client,
        token=data.key,
        webhook=data.webhook,
        webhook_url=data.webhook_url,
        status=get_client_info(data.client)
    ))

@app.route('/webhook', methods=['GET', 'POST'])
def set_webhook():
    data = ApiConfig.query.filter_by(client=g.client_id).first()
    if request.method == 'POST':
        args = request.get_json()
        if not args:
            abort(404, 'payload required!')
        wh, wh_url = args['webhook'], args['webhook_url']
        data.webhook = wh
        data.webhook_url = wh_url
        db.session.commit()
    return jsonify(dict(
            webhook=data.webhook,
            webhook_url=data.webhook_url
        ))
        
@app.route("/")
def hello():
    return "welcome to whatsapp api gateway"

def create_db():
    with app.app_context():
        db.create_all()
        me = ApiConfig(
            client="admin",
            key="bQQfrpMRjV1epvvcnuuBB7hw3xY31NCO",
            webhook=False,
            webhook_url=""
        )
        db.session.add(me)
        db.session.commit()

if __name__ == '__main__':
    if not os.path.exists(BASE_DIR+'/apiwahstapp.db'):
        create_db()
    app.run(host='0.0.0.0')