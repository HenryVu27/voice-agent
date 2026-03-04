from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    deepgram_api_key: str = ""
    deepl_api_key: str = ""
    google_application_credentials: str = ""

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173"]

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
