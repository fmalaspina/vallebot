from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import time, date

class Cliente(BaseModel):
    nombre: str
    telefono: str
    email: Optional[str] = None
    embedding: Optional[List[float]] = None

class Servicio(BaseModel):
    nombre: str
    tipo: Literal["turno", "regular"]
    duracion_min: int
    dias: Optional[List[str]] = None
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None
    embedding: Optional[List[float]] = None

class Agenda(BaseModel):
    fecha: date
    hora: time
    disponible: bool = True
    servicio: str
    cliente: Optional[str] = None
    embedding: Optional[List[float]] = None

class Profesional(BaseModel):
    nombre: str
    especialidad: Optional[str]
    servicios: List[Servicio]
    agenda: Optional[List[Agenda]] = Field(default_factory=list)
    embedding: Optional[List[float]] = None
