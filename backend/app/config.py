# app/config.py
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field, computed_field

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

class Settings(BaseSettings):
    # App
    ENV: str = "dev"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api"

    # DB (override completo si DATABASE_URL presente)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "vallebot"
    DB_PASSWORD: str = "secret"
    DB_NAME: str = "vallebot"
    DB_URL_OVERRIDE: str | None = None

    # Embeddings / LLM
    EMBEDDING_MODEL: str = "all-mpnet-base-v2"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_DIM: int = 768
    EMBEDDING_NORMALIZE: bool = False

    PGVECTOR_DISTANCE: str = "cosine"
    PGVECTOR_INDEX_LISTS: int = 100

    # LLM (si más adelante lo usás)
    LLM_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "llama2:latest"
    LLM_TIMEOUT: int = 60

    # WhatsApp
    WA_VERIFY_TOKEN: str | None = None
    WA_ACCESS_TOKEN: str | None = None
    WA_PHONE_NUMBER_ID: str | None = None

    # CORS
    CORS_ALLOW_ORIGINS: str = "*"

    @computed_field
    @property
    def DATABASE_URL(self) -> str:  # type: ignore[override]
        if self.DB_URL_OVERRIDE:
            return self.DB_URL_OVERRIDE
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @computed_field
    @property
    def CORS_ALLOW_ORIGINS_LIST(self) -> list[str]:  # type: ignore[override]
        if self.CORS_ALLOW_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ALLOW_ORIGINS.split(",") if o.strip()]

    model_config = {"extra": "ignore"}

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
