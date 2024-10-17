from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import setting
from entities.models import db_base

class DatabaseManager:
    def __init__(self, models):
        self.engine = create_engine(setting.DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        models.metadata.create_all(self.engine)

    def get_db_session(self):
        return self.SessionLocal()

db_manager = DatabaseManager(db_base)