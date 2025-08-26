from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any

class InterpretRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Texto ya convertido desde STT del front.")
    candidate_products: Optional[List[str]] = Field(
        default=None, description="Opcional: catálogo de nombres de producto para matching difuso."
    )

class InterpretResponse(BaseModel):
    intent: Literal["crear_venta", "listar_ventas", "ayuda"]
    confidence: float
    entities: Dict[str, Any]
    notes: List[str]
    command: Optional[Dict[str, Any]] = None  # acción sugerida para tu sistema

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1)
    voice: Optional[str] = Field(default="es-PE-CamilaNeural", description="Voz a usar para TTS")
    rate: Optional[str] = Field(default="+0%", description="Velocidad relativa de la voz")
    volume: Optional[str] = Field(default="+0%", description="Volumen relativo de la voz")