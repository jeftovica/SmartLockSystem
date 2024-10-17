from datetime import timedelta
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException
from jwt import InvalidTokenError
from sqlalchemy.orm import Session
from starlette import status

from config import setting
from dependencies.middleware import get_current_user
from entities import models, schemas
from dependencies.database import get_db_session
from entities.models import User
from entities.schemas import Token, TokenData, UserOutput
from services import user_service
from utils.token import create_access_token, oauth2_scheme
from utils.utils import verify_password

user_router = APIRouter()
user_router_path = "/api/user"

@user_router.get(user_router_path)
async def get_user(db:Session = Depends(get_db_session)):
    user = db.query(models.User).filter(models.User.id == 1).first()
    return {"name": user.name, "id": user.id}

@user_router.post(user_router_path)
async def create_user(new_user:schemas.NewUser, db:Session = Depends(get_db_session)):
    user = user_service.get_user_by_email(db, new_user.email)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_service.create_user(db,new_user)
    return {"success": True}


@user_router.post(user_router_path + "/login")
def login_user(payload: schemas.LoginUser, db: Session = Depends(get_db_session)):

    if not payload.email or not payload.password:
        raise HTTPException(status_code=400, detail="Field missing")

    user = user_service.get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(payload.password, user.password):
        raise HTTPException(status_code=404, detail="User not found")
    access_token_expires = timedelta(minutes=setting.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": payload.email}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

@user_router.get(user_router_path + "/me", response_model=UserOutput)
async def get_current_user(current_user: Annotated[User, Depends(get_current_user)]):
   return current_user
