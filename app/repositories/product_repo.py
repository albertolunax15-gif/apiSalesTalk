from typing import Optional, Dict, Any, List
from ..core.firebase import rtdb

PRODUCTS_PATH = "/products"


class ProductRepo:
    @staticmethod
    def get_by_id(product_id: str) -> Optional[Dict[str, Any]]:
        return rtdb(f"{PRODUCTS_PATH}/{product_id}").get()

    @staticmethod
    def upsert(product_id: str, product: Dict[str, Any]) -> None:
        """Crea o actualiza un producto."""
        rtdb(f"{PRODUCTS_PATH}/{product_id}").set(product)

    @staticmethod
    def delete(product_id: str) -> None:
        rtdb(f"{PRODUCTS_PATH}/{product_id}").delete()

    @staticmethod
    def list(limit: int = 50) -> List[Dict[str, Any]]:
        data = rtdb(PRODUCTS_PATH).order_by_key().limit_to_first(limit).get()

        # Validar que la respuesta sea un diccionario
        if not isinstance(data, dict):
            return []

        # Solo incluir productos que realmente sean diccionarios
        return [{"id": k, **v} for k, v in data.items() if isinstance(v, dict)]
