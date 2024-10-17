from typing import Annotated

from fastapi import Depends, HTTPException, status
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from dependencies.database import get_db_session
from entities.schemas import TokenData
from services.user_service import get_user_by_email
from utils.token import oauth2_scheme, decode_access_token


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],
                           db: Annotated[Session, Depends(get_db_session)]):

    try:
        payload = decode_access_token(token)
        if payload is None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        token_data = TokenData(email=email)
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = get_user_by_email(db, token_data.email)
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user