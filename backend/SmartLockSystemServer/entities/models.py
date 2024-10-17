import uuid

from sqlalchemy.orm import foreign, relationship, declarative_base


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
    pin = Column(Integer, nullable=False)
    rfid_key = Column(String, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete='SET NULL'),nullable=False)

class Face(db_base):
    __tablename__ = "faces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String, nullable=False)
    face_number = Column(String, nullable=False)
    face_value = Column(String, nullable=False)
    lock_id = Column(UUID(as_uuid=True), ForeignKey("locks.id", ondelete='SET NULL'),nullable=False)