from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

ProductStatus = Literal["active", "inactive"]

class ProductCreate(BaseModel):
    name: str
    price: float
    status: ProductStatus = "active"

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    status: Optional[ProductStatus] = None

class ProductResponse(BaseModel):
    id: str
    name: str
    price: float
    status: ProductStatus
    created_at: Optional[datetime] = None  # ← igual a tu modelo original

# ← Añadido para /{id}/name (ligero y útil)
class ProductNameResponse(BaseModel):
    id: str
    name: str

//str
