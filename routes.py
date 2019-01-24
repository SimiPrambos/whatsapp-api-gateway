import threading
import requests


class HandleReceivedMessage(threading.Thread):
    def __init__(self, driver_obj, messages_obj, client_id):
        from main import get_data

        self.driver = driver_obj
        self.messages = messages_obj
        self.client = client_id
        self.data = get_data(self.client)
        self.deamon = True
        threading.Thread.__init__(self)

    def run(self):
        for messages in self.messages:
            for message in messages.messages:
                if message.type == 'chat':
                    self.webhook(
                        message.sender.id,
                        message.content,
                        message.timestamp
                    )

    def webhook(self, sender, content, timestamp):
        # data = get_data(self.client)
        if self.data.webhook:
            payload = dict(
                sender=sender,
                content=content,
                time=timestamp.strftime("%H:%M:%S"),
                date=timestamp.strftime("%d/%m/%Y")
            )
            print(payload)
            r = requests.post(self.data.webhook_url, data=payload)
        else:
            pass    

class HandleSendMessage(threading.Thread):
    def __init__(self, driver_obj, sender, content, media=None):
        self.driver = driver_obj
        self.sender = sender if '@c.us' in sender else sender+'@c.us'
        self.content = content
        self.media = media
        print(media)
        print(self.sender)
        self.deamon = True
        threading.Thread.__init__(self)

    def run(self):
        try:
            if self.media:
                self.driver.send_media(self.media, self.sender, self.content)
                print("oke")
            else:
                self.driver.send_message_to_id(self.sender, self.content)
            return True
        except:
            return False
