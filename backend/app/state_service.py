# state_service.py
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from models import (
    Booking, BookingStatus, RelationshipState,
    Payment, PaymentStatus, Profesional, Cliente, Servicio
)
from embedding_service import embed_text

async def refresh_relationship_state(
    session: AsyncSession,
    profesional_id: int,
    cliente_id: int,
    recent_limit: int = 5
):
    prof = await session.get(Profesional, profesional_id)
    cli  = await session.get(Cliente, cliente_id)

    # Próximo booking
    next_res = await session.execute(
        select(Booking)
        .where(
            Booking.profesional_id == profesional_id,
            Booking.cliente_id == cliente_id,
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.ATTENDED, BookingStatus.PENDING])
        )
        .order_by(Booking.fecha, Booking.hora)
        .limit(1)
    )
    next_booking = next_res.scalar_one_or_none()

    # Últimos bookings (historial inverso)
    recent_res = await session.execute(
        select(Booking)
        .where(Booking.profesional_id == profesional_id,
               Booking.cliente_id == cliente_id)
        .order_by(Booking.fecha.desc(), Booking.hora.desc())
        .limit(recent_limit)
    )
    recent_list = list(recent_res.scalars())

    # Pagos verificados
    total_pagado = await session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0.0))
        .where(
            Payment.profesional_id == profesional_id,
            Payment.cliente_id == cliente_id,
            Payment.status == PaymentStatus.VERIFIED
        )
    ) or 0.0

    # Sesiones asistidas * (precio promedio servicio principal) (simplificado)
    # Podés mejorar esto según tu modelo de pricing.
    # Tomo el primer servicio del profesional usado en bookings del cliente.
    servicio_ids_res = await session.execute(
        select(Booking.servicio_id)
        .where(Booking.profesional_id == profesional_id,
               Booking.cliente_id == cliente_id)
        .distinct()
        .limit(1)
    )
    main_servicio_id = servicio_ids_res.scalar_one_or_none()
    costo_estimado = 0.0
    if main_servicio_id:
        serv = await session.get(Servicio, main_servicio_id)
        asistidas = sum(1 for b in recent_list if b.status in (BookingStatus.ATTENDED, BookingStatus.CONFIRMED))
        if serv and serv.precio:
            costo_estimado = asistidas * float(serv.precio)

    pendiente = max(costo_estimado - total_pagado, 0.0)

    state_json = {
        "next_booking": (
            {
                "fecha": next_booking.fecha.isoformat(),
                "hora": next_booking.hora.isoformat(),
                "servicio_id": next_booking.servicio_id,
                "status": next_booking.status.value
            } if next_booking else None
        ),
        "recent_bookings": [
            {
                "fecha": b.fecha.isoformat(),
                "hora": b.hora.isoformat(),
                "status": b.status.value
            } for b in recent_list
        ],
        "total_paid": total_pagado,
        "estimated_cost": costo_estimado,
        "pending_balance": pendiente
    }

    summary_text = build_summary_text(prof, cli, state_json)
    summary_embedding = embed_text(summary_text)

    # Upsert
    existing = await session.execute(
        select(RelationshipState).where(
            RelationshipState.profesional_id == profesional_id,
            RelationshipState.cliente_id == cliente_id
        )
    )
    rs = existing.scalar_one_or_none()
    if rs is None:
        rs = RelationshipState(
            profesional_id=profesional_id,
            cliente_id=cliente_id,
            state_json=state_json,
            summary_text=summary_text,
            summary_embedding=summary_embedding
        )
        session.add(rs)
    else:
        rs.state_json = state_json
        rs.summary_text = summary_text
        rs.summary_embedding = summary_embedding
    await session.commit()
    return rs

def build_summary_text(prof: Profesional, cli: Cliente, sj: dict) -> str:
    nb = sj["next_booking"]
    next_str = (
        f"{nb['fecha']} {nb['hora']} (servicio {nb['servicio_id']}, {nb['status']})"
        if nb else "sin próximo turno"
    )
    hist = ", ".join(f"{r['fecha']} {r['status']}" for r in sj["recent_bookings"]) or "sin historial"
    return (
        f"Profesional: {prof.nombre}. Cliente: {cli.nombre}. "
        f"Próximo: {next_str}. Historial: {hist}. "
        f"Pagado: {sj['total_paid']:.2f}. Estimado: {sj['estimated_cost']:.2f}. "
        f"Saldo pendiente: {sj['pending_balance']:.2f}."
    )
