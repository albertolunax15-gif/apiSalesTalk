from typing import List, Optional
from ..models.product import ProductCreate, ProductResponse
from ..repositories.product_repo import ProductRepo
import uuid


class ProductService:
    @staticmethod
    def create(payload: ProductCreate) -> ProductResponse:
        product_id = str(uuid.uuid4())
        product_data = payload.dict()
        ProductRepo.upsert(product_id, product_data)

        return ProductResponse(id=product_id, **product_data)

    @staticmethod
    def get(product_id: str) -> Optional[ProductResponse]:
        data = ProductRepo.get_by_id(product_id)
        if not data:
            return None
        return ProductResponse(id=product_id, **data)

    @staticmethod
    def list_products(limit: int = 50) -> List[ProductResponse]:
        data = ProductRepo.list(limit)
        return [ProductResponse(**p) for p in data]

    @staticmethod
    def delete(product_id: str) -> None:
        ProductRepo.delete(product_id)