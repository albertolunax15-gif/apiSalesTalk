from typing import Optional, Dict, Any, List
from ..core.firebase import rtdb

SALES_PATH = "/sales"
#Commit

class SaleRepo:
    @staticmethod
    def get_by_id(sale_id: str) -> Optional[Dict[str, Any]]:
        return rtdb(f"{SALES_PATH}/{sale_id}").get()

    @staticmethod
    def upsert(sale_id: str, sale: Dict[str, Any]) -> None:
        """Crea o actualiza una venta."""
        rtdb(f"{SALES_PATH}/{sale_id}").set(sale)

    @staticmethod
    def delete(sale_id: str) -> None:
        rtdb(f"{SALES_PATH}/{sale_id}").delete()

    @staticmethod
    def list(limit: int = 50) -> List[Dict[str, Any]]:
        data = rtdb(SALES_PATH).order_by_key().limit_to_first(limit).get()

        if not isinstance(data, dict):
            return []

        return [{"id": k, **v} for k, v in data.items() if isinstance(v, dict)]

    @staticmethod
    def list_by_product(product_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Lista ventas asociadas a un producto específico."""
        data = (
            rtdb(SALES_PATH)
            .order_by_child("product_id")
            .equal_to(product_id)
            .limit_to_first(limit)
            .get()
        )

        if not isinstance(data, dict):
            return []

        return [{"id": k, **v} for k, v in data.items() if isinstance(v, dict)]
