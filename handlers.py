import threading
from webwhatsapi import MessageGroup
from webwhatsapi.objects.whatsapp_object import WhatsappObject
from flask.json import JSONEncoder

class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = threading.Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False


class WhatsAPIJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, WhatsappObject):
            return obj.get_js_obj()
        if isinstance(obj, MessageGroup):
            return obj.chat
        return super(WhatsAPIJSONEncoder, self).default(obj)