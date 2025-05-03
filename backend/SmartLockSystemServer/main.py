import asyncio
import json
import paho.mqtt.client as mqtt
from fastapi import FastAPI, Depends
import logging

from sqlalchemy.orm import Session

from dependencies.database import get_db_session
from entities.models import Lock
from services import lock_service

host = "localhost"
port = 1883
keepalive = 30
send_topic = f"ToLock"
receive_topic = f"FromLock"

app = FastAPI()
app.isAuthorized = True

client = mqtt.Client(client_id="11111111", clean_session=True)
loop = asyncio.get_event_loop()
logging.basicConfig(filename='log.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger("requests").setLevel(logging.WARNING)
master_tags = []
def on_connect(client, userdata, flags, rc):
    client.subscribe(topic=receive_topic)


def on_message(client, user_data, msg):
    if msg.topic == receive_topic:
        data = json.loads(msg.payload.decode())
        print(data)
        lock_id = data.get('device_id',None)
        if data.get("action", None) == "pinUnlock":
            pin_input = data.get("pin", None)
            db: Session = next(get_db_session())
            lock:Lock = lock_service.get_lock_by_id(db,lock_id)
            if pin_input == lock.pin:
                lock.locked = False
                lock_service.update_lock(db,lock)
                logging.info(f"Successful unlock by pin: {pin_input}")
            else:
                logging.warning(f"Unsuccessful unlock by pin: {pin_input}")
            client.publish(send_topic, json.dumps({"locked": lock.locked}))
        if data.get("action", None) == "getState":
            db: Session = next(get_db_session())
            lock:Lock = lock_service.get_lock_by_id(db,lock_id)
            client.publish(send_topic, json.dumps({"locked": lock.locked}))
        if data.get("action", None) == "lockLock":
            db: Session = next(get_db_session())
            lock:Lock = lock_service.get_lock_by_id(db,lock_id)
            lock.locked = True
            lock_service.update_lock(db,lock)
            client.publish(send_topic, json.dumps({"locked": lock.locked}))
        if data.get("action", None) == "tagUnlock":
            tag_input = data.get("tag", None)
            db: Session = next(get_db_session())
            lock: Lock = lock_service.get_lock_by_id(db, lock_id)
            if tag_input == lock.rfid_key:
                lock.locked = False
                lock_service.update_lock(db, lock)
                logging.info(f"Successful unlock by tag: {tag_input}")
            else:
                logging.warning(f"Unsuccessful unlock by tag: {tag_input}")

            client.publish(send_topic, json.dumps({"locked": lock.locked}))



client.on_message = on_message
client.on_connect = on_connect
client.connect(host, port, keepalive=keepalive)
client.loop_start()