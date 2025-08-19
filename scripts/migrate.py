# scripts/migrate.py
import sys, os, time
from datetime import datetime, timezone

# asegurar que la raíz del proyecto esté en sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.core.firebase import init_firebase, rtdb

MIGRATION_NAME = "2025-08-ensure-users-products-sales-structure-final"
MIGRATIONS_PATH = "/_migrations"
USERS_PATH = "/users"
PRODUCTS_PATH = "/products"
SALES_PATH = "/sales"
EMAIL_INDEX_PATH = "/_indexes/email_to_uid"

def already_ran():
    return bool(rtdb(f"{MIGRATIONS_PATH}/{MIGRATION_NAME}").get())

def mark_done():
    rtdb(f"{MIGRATIONS_PATH}/{MIGRATION_NAME}").set(int(time.time()))

def ensure_branch_exists(path: str):
    """Si la rama no existe (get() is None), crea un placeholder para que se muestre."""
    ref = rtdb(path)
    val = ref.get()
    if val is None:
        print(f"Creando rama: {path}")
        # placeholder visible y sencillo
        ref.set({"__created_by_migration__": True})
    else:
        print(f"Ya existe rama: {path}")

def safe_set(child_path: str, value):
    """Escribe un valor en una ruta concreta (set)"""
    rtdb(child_path).set(value)

def run():
    init_firebase()

    if already_ran():
        print("Migration ya aplicada. Nada que hacer.")
        return

    now = datetime.now(timezone.utc).isoformat()

    # 1) Asegurar que las ramas base existan (usar leading slash para seguir tu patrón)
    ensure_branch_exists(USERS_PATH)
    ensure_branch_exists(PRODUCTS_PATH)
    ensure_branch_exists(SALES_PATH)
    ensure_branch_exists(EMAIL_INDEX_PATH)    # crea _indexes/email_to_uid si falta

    # 2) Normalizar usuarios existentes
    users = rtdb(f"{USERS_PATH}").get() or {}
    if isinstance(users, dict):
        for uid, profile in users.items():
            # Si el profile no es dict (por algún dato corrupto), lo saltamos
            if not isinstance(profile, dict):
                continue
            # password
            if "password" not in profile:
                print(f"Añadiendo password=None a users/{uid}")
                safe_set(f"{USERS_PATH}/{uid}/password", None)
            # created_at
            if "created_at" not in profile:
                print(f"Añadiendo created_at a users/{uid}")
                safe_set(f"{USERS_PATH}/{uid}/created_at", now)
            # disabled
            if "disabled" not in profile:
                print(f"Añadiendo disabled=False a users/{uid}")
                safe_set(f"{USERS_PATH}/{uid}/disabled", False)

    # 3) Normalizar productos existentes
    products = rtdb(f"{PRODUCTS_PATH}").get() or {}
    if isinstance(products, dict):
        for pid, product in products.items():
            if not isinstance(product, dict):
                continue
            if "status" not in product:
                print(f"Añadiendo status='active' a products/{pid}")
                safe_set(f"{PRODUCTS_PATH}/{pid}/status", "active")
            if "created_at" not in product:
                print(f"Añadiendo created_at a products/{pid}")
                safe_set(f"{PRODUCTS_PATH}/{pid}/created_at", now)

    # 4) Normalizar ventas existentes
    sales = rtdb(f"{SALES_PATH}").get() or {}
    if isinstance(sales, dict):
        for sid, sale in sales.items():
            if not isinstance(sale, dict):
                continue
            if "created_at" not in sale:
                print(f"Añadiendo created_at a sales/{sid}")
                safe_set(f"{SALES_PATH}/{sid}/created_at", now)

    # 5) Marcar migración aplicada
    mark_done()
    print("Migration aplicada correctamente.")

if __name__ == "__main__":
    run()
