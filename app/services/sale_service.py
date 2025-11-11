from typing import List, Optional, Literal
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
    def report():
        # Reporte global SIN parámetros: agrupa por día y usa hasta 1000 ventas
        from ..repositories.product_repo import ProductRepo
        from datetime import datetime

        rows = SaleService.list_sales(1000)  # usa tu método existente

        price_cache = {}
        total_sales = 0
        total_revenue = 0.0
        buckets = {}

        for sale in rows:
            dt = getattr(sale, "date", None)
            if not isinstance(dt, datetime):
                continue

            pid = sale.product_id
            if pid not in price_cache:
                prod = ProductRepo.get_by_id(pid)
                price_cache[pid] = float(prod.get("price", 0)) if prod else 0.0

            sale_total = price_cache[pid] * float(sale.quantity or 0)

            total_sales += 1
            total_revenue += sale_total

            key = dt.strftime("%Y-%m-%d")  # agrupa por DÍA
            if key not in buckets:
                buckets[key] = {"count": 0, "total": 0.0}
            buckets[key]["count"] += 1
            buckets[key]["total"] += sale_total

        avg_ticket = (total_revenue / total_sales) if total_sales else 0

        return {
            "group_by": "day",
            "total_sales": total_sales,
            "total_revenue": round(total_revenue, 2),
            "avg_ticket": round(avg_ticket, 2),
            "buckets": [
                {"key": k, "count": v["count"], "total": round(v["total"], 2)}
                for k, v in sorted(buckets.items())
            ],
        }




    @staticmethod
    def delete(sale_id: str) -> None:
        SaleRepo.delete(sale_id)