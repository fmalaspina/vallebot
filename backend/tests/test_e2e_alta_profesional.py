# tests/test_e2e_alta_profesional.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, delete

from app.main import app
from app.db import SessionLocal
from app.models import ProfessionalInvite, Profesional
import logging
logging.basicConfig(level="DEBUG")
TEST_PHONE = "5491110000000"
TEST_NAME = "[TEST] Dra. Ana López"
TEST_BIO = "Psicóloga infanto-juvenil"


def wa_payload(texto: str, phone: str = TEST_PHONE):
    return {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": phone,
                        "id": "wamid.test",
                        "type": "text",
                        "text": {"body": texto}
                    }]
                }
            }]
        }]
    }


@pytest_asyncio.fixture
async def invite_record():
    """Crea invitación previa y la limpia al finalizar."""
    async with SessionLocal() as s:
        inv = ProfessionalInvite(
            telefono=TEST_PHONE,
            consumed=False,
            partial_data={},
            missing_fields=["nombre"]  # primer dato requerido
        )
        s.add(inv)
        await s.commit()
    yield
    async with SessionLocal() as s:
        await s.execute(delete(Profesional).where(Profesional.telefono == TEST_PHONE))
        await s.execute(delete(ProfessionalInvite).where(ProfessionalInvite.telefono == TEST_PHONE))
        await s.commit()


@pytest.mark.asyncio
async def test_alta_incremental(invite_record):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1) Primer mensaje sin nombre -> pending
        # 1) Primer mensaje sin nombre ni patrón claro
        r1 = await ac.post(
            "/webhook/whatsapp",
            json=wa_payload("Hola, soy psicóloga y quiero registrarme")
        )
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["status"] == "pending"        # falta 'nombre'
        assert "Nombre:" in d1["reply"]         # mensaje de instrucción
        

        # 2) Segundo mensaje con Nombre + Bio -> alta
        msg2 = f"Nombre: {TEST_NAME}\nBio: {TEST_BIO}"
        r2 = await ac.post("/webhook/whatsapp", json=wa_payload(msg2))
        assert r2.status_code == 200, r2.text
        d2 = r2.json()
        assert d2["status"] == "ok"
        prof_id = d2["profesional_id"]

        # Verificar en DB
        async with SessionLocal() as s:
            res = await s.execute(select(Profesional).where(Profesional.id == prof_id))
            prof = res.scalar_one()
            assert prof.nombre == TEST_NAME
            assert prof.telefono == TEST_PHONE
            assert prof.embedding is not None
            assert len(prof.embedding) == 768  # ajusta si cambias el modelo

        # 3) Mensaje posterior -> ya registrado
        r3 = await ac.post("/webhook/whatsapp", json=wa_payload("Hola otra vez"))
        assert r3.status_code == 200
        d3 = r3.json()
        assert d3["status"] == "ok"
        assert "Ya estás registrado" in d3["reply"]
