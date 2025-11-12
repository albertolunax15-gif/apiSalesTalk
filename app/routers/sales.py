from fastapi import APIRouter, Depends, HTTPException
from ..core.deps import get_current_user, require_role
from ..services.sale_service import SaleService
from ..models.sale import SaleCreate, SaleResponse

router = APIRouter(prefix="/sales", tags=["sales"])

@router.post("", response_model=SaleResponse)
def create_sale(
    body: SaleCreate,
    current_user: dict = Depends(require_role("superadmin"))  # solo valida el rol
):
    try:
        return SaleService.create(body) 
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=list[SaleResponse])
def list_sales(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)  # 🔒 Cualquier usuario logueado puede ver
):
    return SaleService.list_sales(limit)



@router.get("/report")
def report_sales(_=Depends(get_current_user)):  # mantiene autenticación, sin warning
    return SaleService.report()

@router.delete("/{sale_id}", status_code=204)
def delete_sale(
    sale_id: str,
    current_user: dict = Depends(require_role("superadmin"))  # solo superadmin puede eliminar
):
    try:
        SaleService.delete(sale_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))