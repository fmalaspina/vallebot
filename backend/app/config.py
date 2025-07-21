# app/config.py
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
print(BASE_DIR)
class Settings(BaseSettings):
    ENV: str = "dev"
    LLM_MODEL: str
    LLM_TIMEOUT: int
    OPENAI_API_KEY: str                         # ← requerido
    
    DATABASE_URL: str

    EMBEDDING_MODEL: str
    EMBEDDING_DEVICE: str
    EMBEDDING_DIM: int 
    EMBEDDING_NORMALIZE: bool
    PGVECTOR_DISTANCE: str
    PGVECTOR_INDEX_LISTS: int
    LOG_LEVEL: str
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore",
    )

# singleton
from functools import lru_cache
@lru_cache
def get_settings() -> Settings:
    return Settings()
