import paho.mqtt.client as mqtt
import threading
from selenium import webdriver


broker_address = "3.35.103.224"
# broker_address = "192.168.200.182"
broker_port = 1883
topic = "test01"


class Mqtt_Sub(threading.Thread):
    def __init__(self):
        super().__init__()
        client = mqtt.Client()
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.connect(broker_address, broker_port, 60)
        client.loop_forever()

    def on_connect(self, client, userdata, flags, rc):
        print("connect.." + str(rc))
        if rc == 0:
            client.subscribe(topic)
        else:
            print("연결실패")

    def on_message(self, client, userdata, msg):
        myval = msg.payload.decode("utf-8")
        print(msg.topic + "----" + str(myval))
        
        # if myval.isdecimal():
        #    myval = int(myval)
        #    if myval > 0 and myval < 27:
        driver = webdriver.Chrome(r'/usr/lib/chromium-browser/chromedriver')
        driver.get(f'http://3.35.103.224:8888/tts/?text={myval}')


if __name__ == "__main__":
    try:
        mymqtt = Mqtt_Sub()

    except KeyboardInterrupt:
        print("종료")
