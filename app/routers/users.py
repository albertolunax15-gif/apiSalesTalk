from fastapi import APIRouter, Depends, HTTPException
from ..models.user import UserCreate, UserResponse
from ..services.user_service import UserService
from ..core.deps import get_current_user, require_role

router = APIRouter(prefix="/users", tags=["users"])

@router.post("", response_model=UserResponse)
def create_user(
    body: UserCreate,
    current_user: dict = Depends(require_role("superadmin"))  # 🔒 Solo superadmin
):
    try:
        return UserService.create_if_not_exists(body)
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("", response_model=list[UserResponse])
def list_users(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)  # 🔒 Cualquiera logueado
):
    return UserService.list_users(limit)