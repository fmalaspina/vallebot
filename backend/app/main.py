# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import init_db, get_session
from app.embedding_service import embed_text
from app.models import Profesional
from app.routers import whatsapp  # – agrega invites.router si lo mantienes
import logging
logging.basicConfig(level="DEBUG")
settings = get_settings()

# ---------------------------------------------------------------------------
# Pydantic schemas de entrada
# ---------------------------------------------------------------------------
class ProfesionalIn(BaseModel):
    nombre: str
    telefono: str | None = None
    email: str | None = None
    bio: str | None = None
    especialidad: str | None = None  # la unimos en el texto a embeber


class SemanticQuery(BaseModel):
    query: str
    top_k: int = 3
    scope: str = "profesionales"  # único por ahora


# ---------------------------------------------------------------------------
# Lifespan → creamos tablas, extensión pgvector y “warm‑up” del modelo
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    from app.embedding_service import _load_model  # warm‑up
    _load_model()
    yield


app = FastAPI(title="Vallebot API", lifespan=lifespan)

# Routers (WhatsApp webhook)
app.include_router(whatsapp.router)
# app.include_router(invites.router)  # si lo usas


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "embedding_model": settings.EMBEDDING_MODEL,
        "db": settings.DATABASE_URL,
    }


@app.post("/profesionales", summary="Alta manual (fuera de WhatsApp)")
async def create_profesional(
    data: ProfesionalIn,
    session: AsyncSession = Depends(get_session),
):
    text_src = f"{data.nombre}. Especialidad: {data.especialidad or ''}. {data.bio or ''}"
    prof = Profesional(
        nombre=data.nombre,
        telefono=data.telefono,
        email=data.email,
        bio=data.bio,
        embedding=embed_text(text_src),
    )
    session.add(prof)
    await session.commit()
    await session.refresh(prof)
    return {"id": prof.id, "nombre": prof.nombre}


@app.post("/semantic/search")
async def semantic_search(
    q: SemanticQuery,
    session: AsyncSession = Depends(get_session),
):
    if q.scope != "profesionales":
        raise HTTPException(400, "scope inválido (solo 'profesionales' disponible)")

    vec = embed_text(q.query)
    vec_literal = "[" + ",".join(f"{v:.6f}" for v in vec) + "]"

    sql = text("""
        SELECT id, nombre, embedding <-> :qvec::vector AS distancia
        FROM profesionales
        ORDER BY distancia ASC
        LIMIT :k
    """)

    rows = (
        await session.execute(sql, {"qvec": vec_literal, "k": q.top_k})
    ).mappings().all()

    return {"results": rows, "query": q.query}
