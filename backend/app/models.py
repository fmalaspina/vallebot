from sqlalchemy import Column, Integer, String, Boolean, Date, Time, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class ProfesionalModel(Base):
    __tablename__ = "profesionales"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    especialidad = Column(String)
    servicios = Column(JSON, nullable=False)
    agenda = Column(JSON)
    embedding = Column(Vector(768))  # Ajustá al tamaño real

class ClienteModel(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    telefono = Column(String, nullable=False)
    email = Column(String)
    embedding = Column(Vector(768))

class ServicioModel(Base):
    __tablename__ = "servicios"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    tipo = Column(String, nullable=False)
    duracion_min = Column(Integer, nullable=False)
    dias = Column(JSON)
    hora_inicio = Column(Time)
    hora_fin = Column(Time)
    profesional_id = Column(Integer, ForeignKey("profesionales.id"))
    embedding = Column(Vector(768))

class AgendaModel(Base):
    __tablename__ = "agendas"

    id = Column(Integer, primary_key=True)
    fecha = Column(Date, nullable=False)
    hora = Column(Time, nullable=False)
    disponible = Column(Boolean, default=True)
    servicio = Column(String, nullable=False)
    cliente = Column(String)  # nombre del cliente
    embedding = Column(Vector(768))
