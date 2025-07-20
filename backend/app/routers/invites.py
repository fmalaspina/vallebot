# app/routers/invites.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_session
from app.models import ProfessionalInvite

router = APIRouter(prefix="/invites", tags=["invites"])

class InviteCreateIn(BaseModel):
    telefono: str

class InviteOut(BaseModel):
    id: int
    telefono: str
    consumed: bool

@router.post("", response_model=InviteOut)
async def create_invite(data: InviteCreateIn, session: AsyncSession = Depends(get_session)):
    # ¿Ya existe profesional con ese teléfono?
    existing = await session.execute(select(ProfessionalInvite).where(ProfessionalInvite.telefono == data.telefono))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Ya existe una invitación para ese teléfono")

    inv = ProfessionalInvite(telefono=data.telefono, consumed=False, partial_data={}, missing_fields=["nombre"])
    session.add(inv)
    await session.commit()
    await session.refresh(inv)
    return InviteOut(id=inv.id, telefono=inv.telefono, consumed=inv.consumed)
