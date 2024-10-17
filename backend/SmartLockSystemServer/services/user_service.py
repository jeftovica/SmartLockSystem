from sqlalchemy.orm import Session

from entities import models, schemas
from utils.utils import get_password_hash


def get_user_by_email(db: Session , email:str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session , user:schemas.NewUser):
    db_user = models.User(name=user.name, surname=user.surname, email=user.email, password=get_password_hash(user.password))
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

