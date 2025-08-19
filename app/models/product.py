from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

ProductStatus = Literal["active", "inactive"]


class ProductCreate(BaseModel):
    name: str
    price: float
    status: ProductStatus = "active"


class ProductResponse(BaseModel):
    id: str
    name: str
    price: float
    status: ProductStatus
    created_at: Optional[datetime] = None