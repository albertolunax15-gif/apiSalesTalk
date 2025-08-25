from typing import List, Optional
from datetime import datetime, timezone
import uuid

from fastapi.encoders import jsonable_encoder

from ..models.sale import SaleCreate, SaleResponse
from ..repositories.sale_repo import SaleRepo
from ..repositories.product_repo import ProductRepo


class SaleService:
    @staticmethod
    def create(payload: SaleCreate) -> Optional[SaleResponse]:
        # Validar producto
        product = ProductRepo.get_by_id(payload.product_id)
        if not product:
            raise ValueError("Product does not exist")

        sale_id = str(uuid.uuid4())

        # Convierte Pydantic → JSON
        sale_data = jsonable_encoder(payload)

        # ✅ Si no envían fecha, poner la de ahora (UTC)
        if not sale_data.get("date"):
            sale_data["date"] = datetime.now(timezone.utc).isoformat()

        # ✅ created_at siempre generado en backend
        sale_data["created_at"] = datetime.now(timezone.utc).isoformat()

        SaleRepo.upsert(sale_id, sale_data)

        return SaleResponse(id=sale_id, **sale_data)

    @staticmethod
    def get(sale_id: str) -> Optional[SaleResponse]:
        data = SaleRepo.get_by_id(sale_id)
        if not data:
            return None
        return SaleResponse(id=sale_id, **data)

    @staticmethod
    def list_sales(limit: int = 50) -> List[SaleResponse]:
        data = SaleRepo.list(limit)
        return [SaleResponse(**s) for s in data]

    @staticmethod
    def list_sales_by_product(product_id: str, limit: int = 50) -> List[SaleResponse]:
        data = SaleRepo.list_by_product(product_id, limit)
        return [SaleResponse(**s) for s in data]

    @staticmethod
    def delete(sale_id: str) -> None:
        SaleRepo.delete(sale_id)