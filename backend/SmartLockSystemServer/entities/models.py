import uuid

from sqlalchemy.orm import foreign, relationship, declarative_base
import datetime
from sqlalchemy import DateTime


from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, text, ForeignKey, UUID

db_base=declarative_base()

class User(db_base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String,nullable=False)
    surname = Column(String,nullable=False)
    email = Column(String, nullable=False)
    password = Column(String, nullable=False)

class Lock(db_base):
    __tablename__ = "locks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String, nullable=False)
    pin = Column(String, nullable=False)
    rfid_key = Column(String, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete='SET NULL'),nullable=False)
    locked = Column(Boolean, nullable=False)

class Face(db_base):
    __tablename__ = "faces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String, nullable=False)
    face_number = Column(String, nullable=False)
    face_value = Column(String, nullable=False)
    lock_id = Column(UUID(as_uuid=True), ForeignKey("locks.id", ondelete='SET NULL'),nullable=False)

class LockLog(db_base):
    __tablename__ = "lock_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    lock_id = Column(UUID(as_uuid=True), ForeignKey("locks.id", ondelete="CASCADE"), nullable=False)
    action = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
