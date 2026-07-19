"""Core configuration — loaded from .env, sensible defaults for dev."""
import os
from pydantic_settings import BaseSettings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB = f"sqlite:///{os.path.join(BASE_DIR, 'mantenimiento.db').replace(os.sep, '/')}"


class Settings(BaseSettings):
    # Database
    database_url: str = DEFAULT_DB

    # Paths
    upload_dir: str = os.path.join(BASE_DIR, "uploads")

    # Limits
    max_image_size_mb: int = 10

    # Security (JWT)
    secret_key: str = "ch4ng3-m3-pl34s3-70212352"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480  # 8 hours

    # Admin
    admin_password: str = "Mantt.1"
    admin_dni: str = "70212352"

    # Monitoring
    sentry_dsn: str = ""
    environment: str = "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
