from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_ANON_KEY: str
    SUPABASE_BUCKET: str = "enrollment-photos"

    LOCAL_VIDEOS_PATH: str = "./local_data/videos"
    LOCAL_FRAMES_PATH: str = "./local_data/frames"

    MODEL_DIR: str = "../models"

    CORS_ORIGINS: str = "*"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
