from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

PaymentMethod = Literal["Efectivo", "Tarjeta", "Yape", "Plin"]

class SaleCreate(BaseModel):
    product_id: str
    quantity: int
    payment_method: PaymentMethod = "Efectivo"
    # 👉 OPCIONAL: ya no obliga Swagger/validación
    date: Optional[datetime] = None

    # Controla lo que muestra Swagger en Example
    model_config = {
        "json_schema_extra": {
            "example": {
                "product_id": "2a3b4c",
                "quantity": 2,
                "payment_method": "Efectivo" 
                # intencionalmente SIN "date"
            }
        }
    }

class SaleResponse(BaseModel):
    id: str
    product_id: str
    quantity: int
    payment_method: PaymentMethod
    date: datetime
    created_at: datetime
