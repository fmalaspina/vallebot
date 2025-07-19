from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from backend.app.models import ProfesionalModel, ClienteModel, AgendaModel,ServicioModel
from sqlalchemy import Column, Integer, String, Boolean, Date, Time, JSON, ForeignKey
from app.database import init_db
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código que se ejecuta al iniciar la app
    await init_db()
    yield
    # Código que se ejecuta al cerrar la app (opcional)
    # await cerrar_conexiones()


app = FastAPI(lifespan=lifespan, title="Vallebot RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # cambia a lista concreta en prod
    allow_credentials=True,       # si usás cookies / auth headers
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],         # opcional si querés leer headers custom
    max_age=600,                  # cache del preflight
)
