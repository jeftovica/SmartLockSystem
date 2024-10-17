from uuid import UUID

from pydantic import BaseModel


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