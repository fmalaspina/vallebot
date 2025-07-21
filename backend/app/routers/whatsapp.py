# app/routers/whatsapp.py
import re, json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_session
from app.models import ProfessionalInvite, Profesional
from app.embedding_service import embed_text
from app.config import get_settings
from app.llm_client import achat_completion  # tu wrapper a ollama / OpenAI
import logging
settings = get_settings()
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("whatsapp")
router = APIRouter(prefix="/webhook/whatsapp", tags=["whatsapp"])

# Campos requeridos para crear profesional
REQUIRED_FIELDS = ["nombre"]   # puedes añadir "telefono" si quisieras reconfirmar, etc.

# Regex simples
RE_NOMBRE = re.compile(r'\bNombre\s*:\s*(.+)', re.IGNORECASE)
RE_EMAIL  = re.compile(r'\bEmail\s*:\s*([\w.+-]+@[\w.-]+\.[A-Za-z]{2,})', re.IGNORECASE)
RE_BIO    = re.compile(r'\b(?:Bio|Especialidad|Descripción)\s*:\s*(.+)', re.IGNORECASE)

def simple_parse(texto: str) -> dict:
    """Intento rápido de extraer campos por regex."""
    out = {}
    if m := RE_NOMBRE.search(texto):
        out["nombre"] = m.group(1).strip()
    if m := RE_EMAIL.search(texto):
        out["email"] = m.group(1).strip()
    if m := RE_BIO.search(texto):
        out["bio"] = m.group(1).strip()
    return out

async def llm_parse_if_needed(texto: str) -> dict:
    SYSTEM = (
    "Eres un extractor de datos. Devuelves **EXCLUSIVAMENTE** un JSON "
    "válido con estas claves: nombre, email, bio.\n"
    "- `nombre` debe tener AL MENOS dos palabras con mayúscula inicial.\n"
    "- Si no encuentras un dato, deja el valor \"\".\n"
    "NO añadas explicaciones."
    )

    USER_TEMPLATE = (
        "Extrae datos del siguiente mensaje.\n\n"
        "MENSAJE: «{texto}»"
    )
    

    
    resp = await achat_completion(messages=[{"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER_TEMPLATE.format(texto=texto)}],
            model= settings.LLM_MODEL,
            temperature=0.0,        
            stop=None)
    try:
        return json.loads(resp)
    except Exception:
        return {}

def build_missing_message(missing: list) -> str:
    instrucciones = []
    if "nombre" in missing:
        instrucciones.append("Nombre: Tu nombre completo")
    if "email" in missing:
        instrucciones.append("Email: (opcional) correo de contacto")
    if "bio" in missing:
        instrucciones.append("Bio: breve descripción o especialidad")
    return ("Necesito más datos.\nEnviá un mensaje que contenga líneas como:\n" +
            "\n".join(instrucciones))

@router.post("")
async def whatsapp_webhook(payload: dict, session: AsyncSession = Depends(get_session)):
    """
    Recibe mensajes de WhatsApp Cloud API. Simplicado:
    - Identifica el número
    - Si ya es profesional => responde 'ya registrado'
    - Si invitación no consumida: agrega datos y crea cuando se completa 'nombre'
    """
    # ---- 1. Extraer mensaje y teléfono ----
    try:
        message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
        texto = message["text"]["body"]
        telefono_from = message["from"]
    except (KeyError, IndexError):
        
        resp = {"status": "error", "reply": "Formato WhatsApp inválido"}
        logger.info("Whatsapp response %s",resp)
        return resp

    # ---- 2. ¿Ya es profesional? ----
    prof_res = await session.execute(
        select(Profesional).where(Profesional.telefono == telefono_from)
    )
    prof = prof_res.scalar_one_or_none()
    if prof:
        resp = {
            "status": "ok",
            "reply": f"Ya estás registrado como {prof.nombre}. (Alta previa)"
        }
        logger.info("Whatsapp response %s",resp)
        return resp


    # ---- 3. ¿Existe invitación para ese teléfono? ----
    inv_res = await session.execute(
        select(ProfessionalInvite).where(ProfessionalInvite.telefono == telefono_from)
    )
    invite = inv_res.scalar_one_or_none()
    if not invite:
        resp = {
            "status": "error",
            "reply": "Tu número no está invitado todavía. Pide al administrador que te habilite."
        }
        logger.info("Whatsapp response %s",resp)
        return resp


    if invite.consumed:
        # Consistencia: debería existir profesional, pero por si no
        resp = {
            "status": "warning",
            "reply": "Tu invitación figura consumida, pero no encuentro registro. Contacta al admin."
        }
        logger.info("Whatsapp response %s",resp)
        return resp



    # ---- 4. Parse incremental ----
    parsed = simple_parse(texto)
    logger.info("Whatsapp parsed response %s",parsed)
        
    # Si falta nombre y no lo extrajo regex, podríamos intentar LLM:
    if "nombre" not in parsed:
        llm_extra = await llm_parse_if_needed(texto)
        for k, v in llm_extra.items():
            if k not in parsed and v:
                parsed[k] = v

    # ---- 5. Actualizar partial_data ----
    partial = dict(invite.partial_data)  # copia
    partial.update({k: v for k, v in parsed.items() if v})

    # Determinar faltantes: required que no estén aún
    missing = [f for f in REQUIRED_FIELDS if f not in partial or not partial[f]]

    # (Si quieres volver opcional pedir bio/email posteriormente, puedes condicionar)
    invite.partial_data = partial
    invite.missing_fields = missing

    # ---- 6. ¿Faltan datos? -> pedirlos ----
    if missing:
        await session.commit()
        resp = {
            "status": "pending",
            "reply": build_missing_message(missing),
            "missing": missing
        }
        logger.info("Whatsapp response %s",resp)
        return resp


    # ---- 7. Crear Profesional ----
    nombre = partial["nombre"].strip()
    email = partial.get("email")
    bio = partial.get("bio")

    embedding = embed_text(f"{nombre}. {bio or ''}")
    nuevo = Profesional(
        nombre=nombre,
        telefono=invite.telefono,
        email=email,
        bio=bio,
        embedding=embedding
    )
    logger.info("Whatsapp nuevo profesional: nombre:%s bio:%s telefono:%s", nuevo.nombre,nuevo.bio,nuevo.telefono)
    session.add(nuevo)
    invite.consumed = True
    invite.used_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(nuevo)

    resp = {
        "status": "ok",
        "reply": f"¡Registro exitoso {nuevo.nombre}! Ya podés usar el servicio.",
        "profesional_id": nuevo.id
    }
    logger.info("Whatsapp response %s",resp)
    return resp

