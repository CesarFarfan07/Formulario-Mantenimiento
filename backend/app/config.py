import os
from pydantic_settings import BaseSettings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = f"sqlite:///{os.path.join(BASE_DIR, 'mantenimiento.db').replace(os.sep, '/')}"

class Settings(BaseSettings):
    database_url: str = DEFAULT_DB
    upload_dir: str = "uploads"
    max_image_size_mb: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
