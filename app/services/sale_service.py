from typing import List, Optional
from ..models.sale import SaleCreate, SaleResponse
from ..repositories.sale_repo import SaleRepo
from ..repositories.product_repo import ProductRepo
import uuid


class SaleService:
    @staticmethod
    def create(payload: SaleCreate) -> Optional[SaleResponse]:
        # Validar que el producto exista antes de registrar la venta
        product = ProductRepo.get_by_id(payload.product_id)
        if not product:
            raise ValueError("Product does not exist")

        sale_id = str(uuid.uuid4())
        sale_data = payload.dict()
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