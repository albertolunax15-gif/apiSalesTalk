from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from app.core.firebase import rtdb
from app.models.product import ProductCreate, ProductUpdate

COLLECTION = "products"  # nodo raíz en RTDB: /products/{id}

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _parse_created_at(value: Any) -> Optional[datetime]:
    # Acepta ISO-8601 o None; ignora otros tipos
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None
    return None

def _to_float(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0

def _is_mapping(v: Any) -> bool:
    return isinstance(v, dict)

def _doc_to_response(doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    # data se asume dict; esta función no valida tipos (se valida antes)
    return {
        "id": doc_id,
        "name": data.get("name"),
        "price": _to_float(data.get("price")),
        "status": data.get("status", "active"),
        "created_at": _parse_created_at(data.get("created_at")),
    }

class ProductService:
    # ---------------------------
    # CREATE
    # ---------------------------
    @staticmethod
    def create(data: ProductCreate) -> Dict[str, Any]:
        ref = rtdb(f"/{COLLECTION}")

        name = (data.name or "").strip()
        if not name:
            raise ValueError("El nombre es obligatorio.")

        doc_id = str(uuid.uuid4())
        payload = {
            "name": name,
            "price": _to_float(data.price),
            "status": data.status,
            "created_at": _now_iso(),
        }
        ref.child(doc_id).set(payload)
        return _doc_to_response(doc_id, payload)

    # ---------------------------
    # LIST
    # ---------------------------
    @staticmethod
    def list(limit: int = 50) -> List[Dict[str, Any]]:
        ref = rtdb(f"/{COLLECTION}")
        snap = ref.get()

        items: List[Dict[str, Any]] = []
        if isinstance(snap, dict):
            # Formato esperado: {id: {name, price, ...}, ...}
            for pid, pdata in snap.items():
                if not _is_mapping(pdata):
                    # Ignora basura (bool, str, list, None)
                    continue
                items.append(_doc_to_response(pid, pdata))
        else:
            # Si /products no es un objeto, no rompemos
            items = []

        items.sort(
            key=lambda x: x["created_at"] or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return items[:limit]

    # ---------------------------
    # GET BY ID
    # ---------------------------
    @staticmethod
    def get_by_id(product_id: str) -> Optional[Dict[str, Any]]:
        data = rtdb(f"/{COLLECTION}/{product_id}").get()
        if not _is_mapping(data):
            return None
        return _doc_to_response(product_id, data)

    # ---------------------------
    # UPDATE
    # ---------------------------
    @staticmethod
    def update(product_id: str, data: ProductUpdate) -> Dict[str, Any]:
        ref = rtdb(f"/{COLLECTION}/{product_id}")
        current = ref.get()
        if not _is_mapping(current):
            raise ValueError("Producto no encontrado.")

        updates: Dict[str, Any] = {}

        if data.name is not None:
            updates["name"] = (data.name or "").strip()

        if data.price is not None:
            updates["price"] = _to_float(data.price)

        if data.status is not None:
            updates["status"] = data.status

        if updates:
            ref.update(updates)

        merged = {**current, **updates}
        return _doc_to_response(product_id, merged)

    # ---------------------------
    # DELETE
    # ---------------------------
    @staticmethod
    def delete(product_id: str) -> None:
        ref = rtdb(f"/{COLLECTION}/{product_id}")
        if not _is_mapping(ref.get()):
            raise ValueError("Producto no encontrado.")
        ref.delete()

    # ---------------------------
    # FIND BY NAME (prefijo, sin índices)
    # ---------------------------
    @staticmethod
    def find_by_name(name: str, limit: int = 50) -> List[Dict[str, Any]]:
        prefix = (name or "").strip().lower()
        if not prefix:
            return []

        snap = rtdb(f"/{COLLECTION}").get()
        results: List[Dict[str, Any]] = []
        if isinstance(snap, dict):
            for pid, pdata in snap.items():
                if not _is_mapping(pdata):
                    continue
                pname = (pdata.get("name") or "")
                if pname.lower().startswith(prefix):
                    results.append(_doc_to_response(pid, pdata))

        results.sort(key=lambda x: (x["name"] or "").lower())
        return results[:limit]

    # ---------------------------
    # GET NAME BY ID
    # ---------------------------
    @staticmethod
    def get_name_by_id(product_id: str) -> Optional[Dict[str, str]]:
        name = rtdb(f"/{COLLECTION}/{product_id}/name").get()
        if name is None:
            return None
        # Si el name en RTDB es no-string (corrupción), no rompemos
        if not isinstance(name, str):
            try:
                name = str(name)
            except Exception:
                name = ""
        return {"id": product_id, "name": name}