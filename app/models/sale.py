from pydantic import BaseModel
from typing import Optional, Literal, List
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

GroupBy = Literal["day", "month", "none"]

class SalesReportBucket(BaseModel):
    key: str          # 'YYYY-MM-DD' | 'YYYY-MM' | 'all'
    count: int        # número de ventas en el bucket
    total: float      # ingresos (PEN) en el bucket

class SalesReportResponse(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    group_by: GroupBy = "day"
    currency: str = "PEN"
    total_sales: int
    total_revenue: float
    avg_ticket: float
    buckets: List[SalesReportBucket]
