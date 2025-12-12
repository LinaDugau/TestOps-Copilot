from pydantic_settings import BaseSettings
from typing import Optional
from pydantic import ConfigDict

class Settings(BaseSettings):
    CLOUD_RU_API_KEY: str
    CLOUD_RU_MODEL: str = "Qwen/Qwen3-Next-80B-A3B-Instruct"
    GITLAB_URL: Optional[str] = ""
    GITLAB_TOKEN: Optional[str] = ""

    model_config = ConfigDict(env_file=".env", extra="ignore")

settings = Settings()