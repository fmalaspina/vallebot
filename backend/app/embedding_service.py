# app/embedding_service.py
from sentence_transformers import SentenceTransformer
from functools import lru_cache
from app.config import get_settings

settings = get_settings()

@lru_cache
def _load_model():
    # Usa el nombre correcto del config
    return SentenceTransformer(settings.EMBEDDING_MODEL, device=settings.EMBEDDING_DEVICE)

def embed_text(text: str) -> list[float]:
    model = _load_model()
    vec = model.encode(text)
    return vec.tolist()
