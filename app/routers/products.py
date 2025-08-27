from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query

from ..core.deps import get_current_user, require_role
from ..services.product_service import ProductService
from ..models.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductNameResponse,
)

router = APIRouter(prefix="/products", tags=["products"])

# CREATE
@router.post("", response_model=ProductResponse)
def create_product(
    body: ProductCreate,
    current_user: dict = Depends(require_role("superadmin")),
):
    try:
        return ProductService.create(body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# LIST
@router.get("", response_model=List[ProductResponse])
def list_products(
    limit: int = Query(50, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
):
    return ProductService.list(limit=limit)

# GET BY ID
@router.get("/{product_id}", response_model=ProductResponse)
def get_product_by_id(
    product_id: str,
    current_user: dict = Depends(get_current_user),
):
    doc = ProductService.get_by_id(product_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    return doc

# UPDATE
@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: str,
    body: ProductUpdate,
    current_user: dict = Depends(require_role("superadmin")),
):
    try:
        return ProductService.update(product_id, body)
    except ValueError as e:
        msg = str(e)
        raise HTTPException(status_code=404 if "no encontrado" in msg.lower() else 400, detail=msg)

# DELETE
@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: str,
    current_user: dict = Depends(require_role("superadmin")),
):
    try:
        ProductService.delete(product_id)
        return
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# FIND BY NAME
@router.get("/search/by-name", response_model=List[ProductResponse])
def find_by_name(
    name: str,
    limit: int = Query(50, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
):
    return ProductService.find_by_name(name=name, limit=limit)

# GET NAME BY ID
@router.get("/{product_id}/name", response_model=ProductNameResponse)
def get_name_by_id(
    product_id: str,
    current_user: dict = Depends(get_current_user),
):
    res = ProductService.get_name_by_id(product_id)
    if not res:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    return res