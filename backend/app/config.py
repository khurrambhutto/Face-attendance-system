from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path
import os


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_ANON_KEY: str
    SUPABASE_BUCKET: str = "enrollment-photos"

    LOCAL_VIDEOS_PATH: str = "./local_data/videos"
    LOCAL_FRAMES_PATH: str = "./local_data/frames"

    MODEL_DIR: str = os.environ.get("MODEL_DIR", "../models")

    CORS_ORIGINS: str = "*"

    class Config:
        env_file = str(Path(__file__).resolve().parent.parent / ".env")
        case_sensitive = True


settings = Settings()
