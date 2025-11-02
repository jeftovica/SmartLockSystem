import asyncio
import json
import paho.mqtt.client as mqtt
from fastapi import FastAPI
import logging
from sqlalchemy.orm import Session
from dependencies.database import get_db_session
from entities.models import Lock, LockLog
from services import lock_service
from routers import user_router
from routers import lock_router
from utils.recognizer import Recognizer
import datetime

host = "localhost"
port = 1883
keepalive = 30

send_topic = "ToLock"
receive_topic = "FromLock"

app = FastAPI()
app.isAuthorized = True
app.recognizer = Recognizer()
app.recognizer.recognition_active = True

app.include_router(user_router.user_router, tags=["users"])
app.include_router(lock_router.lock_router, tags=["locks"])

client = mqtt.Client(client_id="11111111", clean_session=True)

lock_router.mqtt_client = client
lock_router.send_topic = send_topic

loop = asyncio.get_event_loop()
logging.basicConfig(filename='log.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger("requests").setLevel(logging.WARNING)


def on_connect(client, userdata, flags, rc):
    client.subscribe(topic=receive_topic)
    logging.info("Connected to MQTT broker, subscribed to %s", receive_topic)

async def broadcast_event_to_ws(lock_id_str: str, payload: dict):
    try:
        conns = lock_router.active_connections.get(lock_id_str, [])
        for conn in conns:
            try:
                await conn.send_json(payload)
            except Exception:
                logging.exception("Failed to send websocket message to connection")
    except Exception:
        logging.exception("broadcast_event_to_ws failed")


def persist_log_and_broadcast(lock: Lock, action: str, method: str = None, result: str = "success", meta: dict = None):
    try:
        db: Session = next(get_db_session())
        log = LockLog(
            lock_id=lock.id,
            action=action if action else method if method else "unknown",
            timestamp=datetime.datetime.utcnow()
        )
        db.add(log)
        db.commit()
        payload = {
            "status": "locked" if lock.locked else "unlocked",
            "action": action if action else method if method else "event",
            "timestamp": log.timestamp.isoformat(),
            "result": result,
            "meta": meta or {}
        }
        asyncio.run_coroutine_threadsafe(broadcast_event_to_ws(str(lock.id), payload), loop)
    except Exception:
        logging.exception("persist_log_and_broadcast failed")


def on_message(client, user_data, msg):
    try:
        if msg.topic != receive_topic:
            return

        data = json.loads(msg.payload.decode())
        logging.info("MQTT received: %s", data)
        lock_id = data.get('device_id', None)

        if not lock_id:
            logging.warning("MQTT message missing device_id: %s", data)
            return

        try:
            db: Session = next(get_db_session())
            lock: Lock = lock_service.get_lock(db, lock_id)
        except Exception:
            logging.exception("Lock not found for device_id=%s", lock_id)
            return

        action = data.get("action", None)

        if action == "pinUnlock":
            pin_input = data.get("pin", None)
            if pin_input is not None and pin_input == lock.pin:
                lock.locked = False
                lock_service.update_lock(db, lock)
                logging.info("Successful unlock by pin for lock %s", lock_id)
                persist_log_and_broadcast(lock, "pinUnlock", method="pin", result="success", meta={"pin": "***"})
            else:
                logging.warning("Unsuccessful unlock by pin for lock %s", lock_id)
                persist_log_and_broadcast(lock, "pinUnlock", method="pin", result="failure")

            client.publish(send_topic, json.dumps({"locked": lock.locked}))

        elif action == "getState":
            client.publish(send_topic, json.dumps({"locked": lock.locked}))
            persist_log_and_broadcast(lock, "getState", method="device_check")

        elif action == "lockLock" or action == "lock":
            lock.locked = True
            lock_service.update_lock(db, lock)
            logging.info("Device requested lock for %s", lock_id)
            client.publish(send_topic, json.dumps({"locked": lock.locked}))
            persist_log_and_broadcast(lock, "lock", method="device")

        elif action == "tagUnlock":
            tag_input = data.get("tag", None)
            if tag_input is not None and tag_input == lock.rfid_key:
                lock.locked = False
                lock_service.update_lock(db, lock)
                logging.info("Successful unlock by tag for lock %s", lock_id)
                persist_log_and_broadcast(lock, "tagUnlock", method="rfid", result="success", meta={"tag": tag_input})
            else:
                logging.warning("Unsuccessful tagUnlock for lock %s", lock_id)
                persist_log_and_broadcast(lock, "tagUnlock", method="rfid", result="failure", meta={"tag": tag_input})

            client.publish(send_topic, json.dumps({"locked": lock.locked}))

        elif action == "faceUnlock" or action == "face":

            person_id = data.get("person_id", None)
            score = data.get("score", None)

            unlocked = data.get("result", "success") == "success"
            if unlocked:
                lock.locked = False
                lock_service.update_lock(db, lock)
                logging.info("Face unlock success for %s (person=%s score=%s)", lock_id, person_id, score)
                persist_log_and_broadcast(lock, "faceUnlock", method="face", result="success", meta={"person_id": person_id, "score": score})
            else:
                logging.warning("Face unlock failed for %s", lock_id)
                persist_log_and_broadcast(lock, "faceUnlock", method="face", result="failure", meta={"person_id": person_id, "score": score})

            client.publish(send_topic, json.dumps({"locked": lock.locked}))

        elif action == "capture":
            loop.create_task(add_person_from_stream())

        else:
            logging.info("Unhandled MQTT action: %s", action)
            persist_log_and_broadcast(lock, action or "unknown", method="device_event", meta=data)

    except Exception:
        logging.exception("Error in MQTT on_message")


client.on_message = on_message
client.on_connect = on_connect
client.connect(host, port, keepalive=keepalive)
client.loop_start()


async def add_person_from_stream():
    success = await app.recognizer.add_verified_person()
    if success:
        client.publish(send_topic, json.dumps({"capture": "done"}), retain=False)
        logging.info("Successfully added new face")
    else:
        client.publish(send_topic, json.dumps({"capture": "fail"}), retain=False)
        logging.info("Failed to add new face")


async def face_recognition_loop():
    while True:
        if app.recognizer.recognition_active:
            person = await app.recognizer.check_for_verified_person()
            if person:
                app.isAuthorized = True
                db: Session = next(get_db_session())

                lock: Lock = lock_service.get_lock(db, 'b71420d0-0e9a-45a8-b668-0d9a6ffacba4')
                lock.locked = False
                lock_service.update_lock(db, lock)

                logging.info("Successfully unlocked by face: %s", person)
                client.publish(send_topic, json.dumps({"locked": lock.locked}), retain=False)

                persist_log_and_broadcast(lock, "faceUnlock", method="face", result="success", meta={"person": str(person)})

                await asyncio.sleep(5)
        await asyncio.sleep(1)


@app.on_event("startup")
async def startup_event():
    loop.create_task(face_recognition_loop())
