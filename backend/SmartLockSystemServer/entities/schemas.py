from uuid import UUID
from pydantic import BaseModel
import datetime


class NewUser(BaseModel):
    name: str
    surname: str
    email: str
    password: str


class LoginUser(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


class UserOutput(BaseModel):
    name: str
    surname: str
    email: str

    class Config:
        from_attributes = True


class LockListOutput(BaseModel):
    id: UUID
    name: str
    locked: bool  # added for lock status

    class Config:
        orm_mode = True


class LockOutput(BaseModel):
    id: UUID
    name: str
    locked: bool

    class Config:
        orm_mode = True


class LockLogOutput(BaseModel):
    id: UUID
    lock_id: UUID
    action: str
    timestamp: datetime.datetime

    class Config:
        orm_mode = True

class ChangePinRequest(BaseModel):
    current_pin: str
    new_pin: str
    lock_id:UUID
