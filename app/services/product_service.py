from typing import List, Optional
import uuid
from datetime import datetime, timezone

from fastapi.encoders import jsonable_encoder

from ..models.product import ProductCreate, ProductResponse
from ..repositories.product_repo import ProductRepo


class ProductService:
    @staticmethod
    def create(payload: ProductCreate) -> ProductResponse:
        product_id = str(uuid.uuid4())

        # Convierte Pydantic → tipos JSON (evita problemas con datetime, Decimals, etc.)
        product_data = jsonable_encoder(payload)

        # ✅ Timestamp ISO8601 en UTC (no será null)
        product_data["created_at"] = datetime.now(timezone.utc).isoformat()

        # Persistir en tu repositorio (Firebase RTDB u otro)
        ProductRepo.upsert(product_id, product_data)

        # Filtra a los campos definidos en el response model
        response_data = {k: v for k, v in product_data.items() if k in ProductResponse.model_fields}

        return ProductResponse(id=product_id, **response_data)

    @staticmethod
    def get(product_id: str) -> Optional[ProductResponse]:
        data = ProductRepo.get_by_id(product_id)
        if not data:
            return None
        response_data = {k: v for k, v in data.items() if k in ProductResponse.model_fields}
        return ProductResponse(id=product_id, **response_data)

    @staticmethod
    def list_products(limit: int = 50) -> List[ProductResponse]:
        data = ProductRepo.list(limit)
        products: List[ProductResponse] = []
        for p in data:
            filtered = {k: v for k, v in p.items() if k in ProductResponse.model_fields or k == "id"}
            pid = filtered.pop("id", None) or p.get("id")
            products.append(ProductResponse(id=pid, **{k: v for k, v in filtered.items() if k in ProductResponse.model_fields}))
        return products

    @staticmethod
    def delete(product_id: str) -> None:
        ProductRepo.delete(product_id)