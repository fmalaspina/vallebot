import os
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv
from app.models import Base
from sqlalchemy import text
# Cargar .env
load_dotenv()

# URL del tipo: postgresql+asyncpg://usuario:clave@host:puerto/db
DATABASE_URL = os.getenv("DATABASE_URL")

# Crear el motor asíncrono
engine = create_async_engine(DATABASE_URL, echo=True)

# Función para crear las tablas
async def init_db():
    async with engine.begin() as conn:
        # Necesario para extensiones como pgvector
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        # Crear las tablas si no existen
        await conn.run_sync(Base.metadata.create_all)
