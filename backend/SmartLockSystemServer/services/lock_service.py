from sqlalchemy.orm import Session
from entities import models
from uuid import UUID
from fastapi import HTTPException, status
from datetime import datetime, timedelta

def get_lock_by_id(db: Session, lock_id: UUID, user_id: UUID):

    lock = db.query(models.Lock).filter(
        models.Lock.id == lock_id,
        models.Lock.owner_id == user_id
    ).first()

    if not lock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lock not found"
        )
    return lock

def get_lock(db: Session, lock_id: UUID):

    lock = db.query(models.Lock).filter(
        models.Lock.id == lock_id
    ).first()

    if not lock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lock not found"
        )
    return lock


def update_lock(db: Session, lock: models.Lock):
    db.merge(lock)
    db.commit()
    db.refresh(lock)
    return lock


def get_locks_for_user(db: Session, user_id: UUID):

    return db.query(models.Lock).filter(models.Lock.owner_id == user_id).all()


def get_logs_for_lock(db: Session, lock_id: UUID):
    cutoff = datetime.utcnow() - timedelta(hours=24)

    return (
        db.query(models.LockLog)
        .filter(
            models.LockLog.lock_id == lock_id,
            models.LockLog.timestamp >= cutoff
        )
        .order_by(models.LockLog.timestamp.desc())
        .all()
    )

def update_pin(db: Session, lock_id: UUID, user_id: UUID, new_pin: str):
    print(user_id, new_pin, lock_id)
    lock = db.query(models.Lock).filter(
        models.Lock.id == lock_id
    ).first()

    if not lock:
        return None

    lock.pin = new_pin
    db.commit()
    db.refresh(lock)
    return lock