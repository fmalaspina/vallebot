# app/llm_client.py
"""
Cliente liviano para llamar a un modelo LLM expuesto vía HTTP
(por ejemplo, Ollama con llama2).

Variables leídas de app.config.Settings:
    LLM_BASE_URL   →  'http://localhost:11434'
    LLM_MODEL      →  'llama2:latest'
    LLM_TIMEOUT    →  segundos (default 60)

Funciona tanto síncrono como asíncrono (httpx).
"""


from __future__ import annotations
import logging
import json
from typing import Any, Iterable, AsyncIterator, Iterator, Dict, Mapping, Optional

import httpx
from sqlalchemy import Sequence
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("llm")
# -------------------------------------------------------------
# Helpers
# -------------------------------------------------------------
_HEADERS = {"Content-Type": "application/json"}
_TIMEOUT = httpx.Timeout(settings.LLM_TIMEOUT or 60.0)


def _format_chat(
    prompt: str,
    system_prompt: Optional[str] = None,
    *,
    temperature: float = 0.7,
    max_tokens: int = 512,
    stream: bool = False,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Construye el payload para /api/chat (formato Ollama).
    Ajustá keys si tu servidor usa otra spec.
    """
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    return {
        "model": model or settings.LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }


# -------------------------------------------------------------
# SYNC
# -------------------------------------------------------------
def chat_completion(
    prompt: str,
    *,
    system_prompt: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 512,
    stream: bool = False,
    model: str | None = None,
) -> str | Iterator[str]:
    """
    Llama al LLM y devuelve:
        - str con la respuesta completa (si stream=False)
        - iterator de str (si stream=True)
    """
    payload = _format_chat(
        prompt,
        system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
        model=model,
    )
    url = f"{settings.LLM_BASE_URL}/api/chat"

    with httpx.Client(timeout=_TIMEOUT, headers=_HEADERS) as client:
        if stream:
            logger.debug("LLM prompt → %s", payload["messages"])
            r = client.post(url, json=payload, stream=True)
            r.raise_for_status()
            # Cada línea es un JSON con {"message": {"content": "…" }, ...}
            def _gen() -> Iterator[str]:
                for line in r.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    yield data.get("message", {}).get("content", "")
            return _gen()
        else:
            logger.debug("LLM prompt → %s", payload["messages"])
            r = client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            return data["message"]["content"]


# -------------------------------------------------------------
# ASYNC
# -------------------------------------------------------------
async def achat_completion(
     *,                                         # Fuerza uso 100 % por keyword
    messages: Sequence[Mapping[str, str]] | None = None,
    prompt: str | None = None,                # compat. con la firma antigua
    model: str = "llama2:latest",
    temperature: float = 0.0,
    stream: bool = False,
    **extra,
) -> str | AsyncIterator[str]:
    """
    Wrapper async para /api/chat de Ollama o similar.

    - Si se pasa `prompt` (str) lo convertimos a messages = [{"role":"user",...}]
    - Devuelve el contenido completo (str). Si `stream=True` yield‑ea fragmentos.
    """
    if prompt and not messages:
        messages = [{"role": "user", "content": prompt}]
    if not messages:
        raise ValueError("Debes pasar `messages` o `prompt`")

    payload = {
        "model": model,
        "messages": list(messages),
        "temperature": temperature,
         "stream": False, 
        **extra,
    }

    logger.debug("LLM prompt → %s", messages)
    url = f"{settings.LLM_BASE_URL}/api/chat"

    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS) as client:
        if stream:
            logger.debug("LLM prompt → %s", payload["messages"])
            r = await client.post(url, json=payload, stream=True)
            r.raise_for_status()

            async def _agen() -> AsyncIterator[str]:
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    yield data.get("message", {}).get("content", "")
            logger.debug("LLM answer ← %s", data)
            return _agen()
        else:
            logger.debug("LLM prompt → %s", payload["messages"])
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            logger.debug("LLM answer ← %s", data)
            return data["message"]["content"]
