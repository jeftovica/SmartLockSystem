from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from sqlalchemy.orm import Session
from dependencies.database import get_db_session
from dependencies.middleware import get_current_user  # used for REST endpoints auth
from entities.models import User, LockLog, Lock
from entities.schemas import LockListOutput, LockLogOutput
from services import lock_service
from typing import List
import datetime
import logging
import json
import uuid as _uuid
from entities.schemas import ChangePinRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

lock_router = APIRouter()
lock_router_path = "/locks"

mqtt_client = None
send_topic = None

active_connections: dict = {}


@lock_router.get(lock_router_path, response_model=list[LockListOutput])
async def get_my_locks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    return lock_service.get_locks_for_user(db, current_user.id)


@lock_router.get("/locks/{lock_id}/status")
async def get_lock_status(
    lock_id: _uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    lock = lock_service.get_lock_by_id(db, lock_id, current_user.id)
    return {"id": lock.id, "locked": lock.locked}


@lock_router.post("/locks/{lock_id}/{action}")
async def toggle_lock(
    lock_id: _uuid.UUID,
    action: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    lock = lock_service.get_lock_by_id(db, lock_id, current_user.id)

    if action not in ["lock", "unlock"]:
        return {"error": "Invalid action"}

    new_state = True if action == "lock" else False
    lock.locked = new_state

    log = LockLog(
        lock_id=lock.id,
        action=action,
        timestamp=datetime.datetime.utcnow()
    )
    db.add(log)
    db.commit()
    db.refresh(lock)

    try:
        if mqtt_client is not None and send_topic is not None:
            command_id = str(_uuid.uuid4())
            mqtt_payload = {
                "command_id": command_id,
                "action": action,
                "lock_id": str(lock.id),
                "issued_by": str(current_user.id),
                "locked": lock.locked,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            mqtt_client.publish(send_topic, json.dumps(mqtt_payload))
    except Exception as e:
        logger.exception("Failed to publish MQTT command: %s", e)

    conns = active_connections.get(str(lock_id), [])
    for conn in conns:
        try:
            await conn.send_json({
                "status": "locked" if new_state else "unlocked",
                "action": action,
                "timestamp": log.timestamp.isoformat()
            })
        except Exception:
            logger.exception("Failed to send websocket message")

    return {"id": lock.id, "locked": lock.locked}


@lock_router.get("/locks/{lock_id}/logs", response_model=List[LockLogOutput])
async def get_lock_logs(
    lock_id: _uuid.UUID,
    db: Session = Depends(get_db_session)
):
    return lock_service.get_logs_for_lock(db, lock_id)


@lock_router.post("/locks/changepin")
async def change_pin(
        data: ChangePinRequest,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db_session)
):
    lock = lock_service.get_lock_by_id(db, data.lock_id, current_user.id)

    if lock.pin != data.current_pin:
        raise HTTPException(status_code=400, detail="Incorrect current PIN")

    updated_lock = lock_service.update_pin(db, data.lock_id, current_user.id, data.new_pin)
    if not updated_lock:
        raise HTTPException(status_code=404, detail="Lock not found")


    log = LockLog(
        lock_id=lock.id,
        action="change_pin",
        timestamp=datetime.datetime.utcnow()
    )
    db.add(log)
    db.commit()

    conns = active_connections.get(str(data.lock_id), [])
    for conn in conns:
        try:
            await conn.send_json({
                "status": "locked" if lock.locked else "unlocked",
                "action": "change_pin",
                "timestamp": log.timestamp.isoformat()
            })
        except Exception:
            logger.exception("Failed to send websocket message on change_pin")

    return {"message": "PIN changed successfully", "new_pin": lock.pin}

@lock_router.websocket("/locks/{lock_id}/ws")
async def websocket_endpoint(websocket: WebSocket, lock_id: str):

    await websocket.accept()

    lock_key = str(lock_id)
    if lock_key not in active_connections:
        active_connections[lock_key] = []
    active_connections[lock_key].append(websocket)

    try:
        while True:

            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_connections.get(lock_key, []):
            active_connections[lock_key].remove(websocket)
