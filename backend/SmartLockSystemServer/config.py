from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    DATABASE_URL: str


    class Config:
        env_file = Path(Path(__file__).resolve().parent) / ".env"


setting = Settings()