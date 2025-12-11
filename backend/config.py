from pydantic_settings import BaseSettings
from typing import Optional
from pydantic import ConfigDict
import os

# Определяем путь к .env файлу в backend директории
_env_file = os.path.join(os.path.dirname(__file__), ".env")

class Settings(BaseSettings):
    CLOUD_RU_API_KEY: Optional[str] = ""
    CLOUD_RU_MODEL: str = "Qwen/Qwen3-Next-80B-A3B-Instruct"
    GITLAB_URL: Optional[str] = ""
    GITLAB_TOKEN: Optional[str] = ""

    model_config = ConfigDict(env_file=_env_file, extra="ignore")

settings = Settings()