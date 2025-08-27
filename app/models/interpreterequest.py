from __future__ import annotations
from typing import Any, Dict, List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field

PaymentMethod = Literal["Efectivo", "Tarjeta", "Yape", "Plin", "Transferencia"]

# -------------------------
# Interpret
# -------------------------
class InterpretRequest(BaseModel):
    text: str = Field(..., description="Frase del usuario (STT final).")
    # Opcional: catálogo parcial local para ayudar en el matching
    candidate_products: Optional[List[Any]] = Field(default=None, description="Opcional: lista local de candidatos (ids/nombres).")

class InterpretResponse(BaseModel):
    intent: str
    confidence: float
    entities: Dict[str, Any]
    notes: List[str] = []
    # Sugerencia/acción que la UI podría ejecutar
    command: Optional[Dict[str, Any]] = None

    # === NUEVO ===
    needs_confirmation: bool = False
    # Lista para UI cuando falte/sea ambiguo el product_id
    candidates: Optional[List[Dict[str, Any]]] = None  # [{id,name,score}]

# -------------------------
# Confirm Sale
# -------------------------
class ConfirmSaleRequest(BaseModel):
    product_id: str
    quantity: int = 1
    payment_method: PaymentMethod = "Efectivo"
    date: Optional[datetime] = None  # si no viene, SaleService pondrá "ahora" (UTC)

class ConfirmSaleResponse(BaseModel):
    # Puedes reusar SaleResponse del dominio si prefieres
    id: str
    product_id: str
    quantity: int
    payment_method: PaymentMethod
    date: datetime
    created_at: datetime