from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

PaymentMethod = Literal["Efectivo", "Yape", "Transferencia", "Plin"]


class SaleCreate(BaseModel):
    date: datetime
    quantity: int
    product_id: str
    payment_method: PaymentMethod


class SaleResponse(BaseModel):
    id: str
    date: datetime
    quantity: int
    product_id: str
    payment_method: PaymentMethod
    created_at: Optional[datetime] = None