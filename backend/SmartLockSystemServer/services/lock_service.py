from sqlalchemy.orm import Session

from entities import models


def get_lock_by_id(db: Session , id:str):
    print(db,id)
    return db.query(models.Lock).filter(models.Lock.id == id).first()

def update_lock(db:Session , lock:models.Lock):
    db.merge(lock)
    db.commit()
    db.refresh(lock)
    return lock