# app/db.py
from __future__ import annotations
from typing import AsyncGenerator, Sequence
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
from sqlalchemy import text
from app.config import get_settings
from app.models import Base

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    class_=AsyncSession,
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

def _opclass() -> str:
    d = settings.PGVECTOR_DISTANCE.lower()
    if d.startswith("cos"):
        return "vector_cosine_ops"
    if d in ("l2", "euclidean", "euclid"):
        return "vector_l2_ops"
    if d in ("ip", "inner_product", "dot"):
        return "vector_ip_ops"
    return "vector_cosine_ops"

INDEX_TARGETS: Sequence[tuple[str, str, str]] = (
    ("profesionales", "embedding", "idx_profesionales_embedding_ivf"),
)

async def _table_exists(conn, table: str) -> bool:
    res = await conn.execute(text("""
        SELECT 1 FROM pg_class c
         JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE c.relkind='r' AND c.relname=:t
    """), {"t": table})
    return res.scalar_one_or_none() is not None

async def _create_index(conn, table: str, col: str, name: str, opclass: str, lists: int):
    await conn.execute(text(f"""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE c.relname='{name}'
      ) THEN
        EXECUTE 'CREATE INDEX {name} ON {table} USING ivfflat ({col} {opclass}) WITH (lists={lists})';
      END IF;
    END$$;
    """))

async def init_db():
    lists = settings.PGVECTOR_INDEX_LISTS
    opclass = _opclass()
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.create_all)
        for table, col, idx in INDEX_TARGETS:
            if await _table_exists(conn, table):
                await _create_index(conn, table, col, idx, opclass, lists)
        await conn.execute(text("ANALYZE;"))
