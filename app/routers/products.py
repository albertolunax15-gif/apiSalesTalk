from fastapi import APIRouter, Depends, HTTPException
from ..core.deps import get_current_user, require_role
from ..services.product_service import ProductService
from ..models.product import ProductCreate, ProductResponse

router = APIRouter(prefix="/products", tags=["products"])

@router.post("", response_model=ProductResponse)
def create_product(
    body: ProductCreate,
    current_user: dict = Depends(require_role("superadmin"))  # 🔒 Solo rol superadmin puede crear
):
    try:
        return ProductService.create(body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[ProductResponse])
def list_products(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)  # 🔒 Cualquier usuario logueado puede ver
):
    return ProductService.list_products(limit)