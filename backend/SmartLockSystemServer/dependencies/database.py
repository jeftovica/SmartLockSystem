from utils.database_manager import db_manager


def get_db_session():
    db = db_manager.get_db_session()
    try:
        yield db
    finally:
        db.close()