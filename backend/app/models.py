# models.py (versión embeddings obligatorios)
from __future__ import annotations
from datetime import datetime, date, time, timezone
from typing import List, Dict, Any, Optional
import enum

from sqlalchemy import (
    String, Integer, Date, Time, DateTime, Boolean, Float, Enum as SAEnum,
    ForeignKey, UniqueConstraint, Index, Text
) 
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from pgvector.sqlalchemy import Vector

VECTOR_DIM = 768  # all-mpnet-base-v2
UTC = timezone.utc
class Base(DeclarativeBase):
    pass

# -------- Enums --------
class ServicioTipo(enum.Enum):
    TURNO = "turno"
    GRUPAL = "grupal"

class BookingStatus(enum.Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    ATTENDED = "ATTENDED"
    NO_SHOW = "NO_SHOW"

class PaymentStatus(enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

# ---------------------------------------------------------------------------
# Profesional – puede tener N servicios
# ---------------------------------------------------------------------------
class Profesional(Base):
    __tablename__ = "profesionales"

    id:        Mapped[int]            = mapped_column(primary_key=True)
    nombre:    Mapped[str]            = mapped_column(String, nullable=False)
    telefono:  Mapped[str]            = mapped_column(String, unique=True, nullable=False)
    email:     Mapped[Optional[str]]  = mapped_column(String)
    bio:       Mapped[Optional[str]]  = mapped_column(String)

    # Embedding para busquedas semánticas
    embedding: Mapped[List[float]]    = mapped_column(Vector(VECTOR_DIM), nullable=False)

    created_at: Mapped[datetime]      = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # 🔹 RELACIÓN: lista de servicios que brinda
    servicios: Mapped[List["Servicio"]] = relationship(
        back_populates="profesional",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Cliente(Base):
    __tablename__ = "clientes"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), index=True)
    telefono: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(150))
    active: Mapped[bool] = mapped_column(default=True)
    notas: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(UTC))
    embedding: Mapped[List[float]] = mapped_column(Vector(VECTOR_DIM), nullable=False)

class Servicio(Base):
    __tablename__ = "servicios"
    id: Mapped[int] = mapped_column(primary_key=True)
    profesional_id: Mapped[int] = mapped_column(ForeignKey("profesionales.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(150))
    tipo: Mapped[ServicioTipo] = mapped_column(SAEnum(ServicioTipo))
    duracion_min: Mapped[int]
    capacidad: Mapped[Optional[int]]
    precio: Mapped[Optional[float]]
    cancellation_limit_min: Mapped[Optional[int]]
    ubicacion_text: Mapped[Optional[str]] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(default=True)
    embedding: Mapped[List[float]] = mapped_column(Vector(VECTOR_DIM), nullable=False)

    profesional: Mapped["Profesional"] = relationship(back_populates="servicios")
    bookings: Mapped[List["Booking"]] = relationship(back_populates="servicio", cascade="all, delete-orphan")

class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(primary_key=True)
    servicio_id: Mapped[int] = mapped_column(ForeignKey("servicios.id"), index=True)
    profesional_id: Mapped[int] = mapped_column(ForeignKey("profesionales.id"), index=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    hora: Mapped[time] = mapped_column(Time)
    cliente_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clientes.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(10))  # 'turno' | 'clase'
    status: Mapped[BookingStatus] = mapped_column(SAEnum(BookingStatus), default=BookingStatus.CONFIRMED)
    capacity_used: Mapped[int] = mapped_column(default=1)
    capacity_total: Mapped[Optional[int]]
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now(UTC), onupdate=datetime.utcnow)

    servicio: Mapped["Servicio"] = relationship(back_populates="bookings")
    enrollments: Mapped[List["Enrollment"]] = relationship(back_populates="booking", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_booking_unique_turno",
              "servicio_id", "fecha", "hora", "cliente_id",
              unique=True,
              postgresql_where=(cliente_id.isnot(None))),  # type: ignore
    )

class Enrollment(Base):
    __tablename__ = "enrollments"
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), index=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="ENROLLED")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(UTC))

    booking: Mapped["Booking"] = relationship(back_populates="enrollments")

    __table_args__ = (
        UniqueConstraint("booking_id", "cliente_id", name="uq_enrollment_booking_cliente"),
    )

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), index=True)
    profesional_id: Mapped[int] = mapped_column(ForeignKey("profesionales.id"), index=True)
    servicio_id: Mapped[Optional[int]] = mapped_column(ForeignKey("servicios.id"))
    booking_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bookings.id"))
    amount: Mapped[float]
    currency: Mapped[str] = mapped_column(String(10), default="ARS")
    method: Mapped[Optional[str]] = mapped_column(String(30))
    status: Mapped[PaymentStatus] = mapped_column(SAEnum(PaymentStatus), default=PaymentStatus.PENDING)
    comprobante_url: Mapped[Optional[str]] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(UTC))
    verified_at: Mapped[Optional[datetime]]

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    direction: Mapped[str] = mapped_column(String(3))  # IN / OUT
    raw_sender: Mapped[str] = mapped_column(String(50), index=True)
    profesional_id: Mapped[Optional[int]] = mapped_column(ForeignKey("profesionales.id"))
    cliente_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clientes.id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(UTC))
    interpreted_action_id: Mapped[Optional[int]] = mapped_column(ForeignKey("interpreted_actions.id"))

class InterpretedAction(Base):
    __tablename__ = "interpreted_actions"
    id: Mapped[int] = mapped_column(primary_key=True)
    intent: Mapped[str] = mapped_column(String(40))
    confidence: Mapped[float]
    raw_json: Mapped[Dict[str, Any]] = mapped_column(JSONB)
    missing: Mapped[List[str]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(20), default="PROCESSED")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(UTC))

class RelationshipState(Base):
    __tablename__ = "relationship_state"
    id: Mapped[int] = mapped_column(primary_key=True)
    profesional_id: Mapped[int] = mapped_column(ForeignKey("profesionales.id"), index=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), index=True)
    state_json: Mapped[Dict[str, Any]] = mapped_column(JSONB)
    summary_text: Mapped[str] = mapped_column(Text)
    summary_embedding: Mapped[List[float]] = mapped_column(Vector(VECTOR_DIM), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("profesional_id", "cliente_id", name="uq_rel_state_prof_cli"),
    )

# Índices adicionales
Index("ix_payment_status_prof", Payment.profesional_id, Payment.status)
Index("ix_messages_sender_created", Message.raw_sender, Message.created_at)
Index("ix_booking_prof_fecha", Booking.profesional_id, Booking.fecha)
class ProfessionalInvite(Base):
    __tablename__ = "professional_invites"
    id: Mapped[int] = mapped_column(primary_key=True)
    telefono: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    partial_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    missing_fields: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    profesional_id: Mapped[Optional[int]] = mapped_column(ForeignKey("profesionales.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))