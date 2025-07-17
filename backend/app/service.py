from pydantic import BaseModel, Field
from typing import Dict, Optional

class ServiceAdd(BaseModel):
    tipo: str = Field(
        description="Categoría: 'cliente', 'cabaña', 'profesional', etc."
    )
    contenido: str = Field(description="Texto libre que se vectorizará")
    metadatos: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Datos adicionales que quieras asociar al vector"
    )