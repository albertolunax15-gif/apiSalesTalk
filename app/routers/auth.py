from fastapi import APIRouter, Depends, HTTPException, status
from ..models.user import UserResponse
from ..services.auth_service import AuthService
from ..core.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(email: str, password: str):
    """
    Genera un JWT válido si las credenciales son correctas.
    """
    token = AuthService.login(email, password)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)):
    """
    Devuelve la información del usuario autenticado a partir del token.
    """
    return current_user