# app/llm_client.py
"""
Cliente liviano para llamar a un modelo LLM (OpenAI ChatGPT)
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Iterator, Mapping, Optional, Sequence

from openai import OpenAI, AsyncOpenAI  # SDK ≥ 1.14
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("llm")

# ------------------------------------------------------------------
# OpenAI clients (se trae la API‑KEY de la variable de entorno)
# ------------------------------------------------------------------
# Podés setear OPENAI_API_BASE o OPENAI_ORG si hiciera falta.
_api_key = settings.OPENAI_API_KEY
_client_sync = OpenAI(api_key=_api_key,timeout=settings.LLM_TIMEOUT or 60.0)
_client_async = AsyncOpenAI(api_key=_api_key,timeout=settings.LLM_TIMEOUT or 60.0)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _build_messages(
    prompt: str | None = None,
    system_prompt: str | None = None,
    messages: Sequence[Mapping[str, str]] | None = None,
) -> list[dict[str, str]]:
    """
    Convierte prompt/ system_prompt al formato de OpenAI.
    Si ya viene `messages`, los devuelve tal cual.
    """
    if messages is not None:
        return list(messages)

    built: list[dict[str, str]] = []
    if system_prompt:
        built.append({"role": "system", "content": system_prompt})
    if prompt:
        built.append({"role": "user", "content": prompt})
    return built


# ------------------------------------------------------------------
# SYNC
# ------------------------------------------------------------------
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
    Llama al modelo:

    • stream = False → devuelve el texto completo.
    • stream = True  → devuelve un generador con los fragmentos.
    """
    model = model or settings.LLM_MODEL or "gpt-4o-mini"
    messages = _build_messages(prompt, system_prompt)

    logger.info("LLM prompt → %s", messages)

    if stream:
        response = _client_sync.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        logger.info("LLM response → %s", response)

        def _gen() -> Iterator[str]:
            for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content

        return _gen()
    else:
        response = _client_sync.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        logger.info("LLM response → %s", response)

        return response.choices[0].message.content


# ------------------------------------------------------------------
# ASYNC
# ------------------------------------------------------------------
async def achat_completion(
    *,                                         # uso 100 % keyword‑only
    messages: Sequence[Mapping[str, str]] | None = None,
    prompt: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
    stream: bool = False,
    **extra,                                  # para compatibilidad futura
) -> str | AsyncIterator[str]:
    """
    Wrapper async que replica la firma del cliente original.
    """
    if prompt is None and messages is None:
        raise ValueError("Debes pasar `messages` o `prompt`")

    model = model or settings.LLM_MODEL or "gpt-4o-mini"
    msgs = _build_messages(prompt, None, messages)

    logger.info("LLM prompt → %s", msgs)

    if stream:
        response = await _client_async.chat.completions.create(
            model=model,
            messages=msgs,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **extra,
        )
        logger.info("LLM response → %s", response)

        async def _agen() -> AsyncIterator[str]:
            async for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content

        return _agen()
    else:
        response = await _client_async.chat.completions.create(
            model=model,
            messages=msgs,
            temperature=temperature,
            max_tokens=max_tokens,
            **extra,
        )
        logger.info("LLM response → %s", response)

        return response.choices[0].message.content
