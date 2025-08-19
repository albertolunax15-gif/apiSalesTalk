from typing import Optional, List
from passlib.context import CryptContext
from ..models.user import UserCreate, UserResponse
from ..repositories.user_repo import UserRepo

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService:
    @staticmethod
    def create_if_not_exists(payload: UserCreate, password: str) -> UserResponse:
        # 1) Buscar por email en repositorio
        existing = UserRepo.get_by_email(payload.email)
        if existing:
            raise Exception("El usuario ya existe")

        # 2) Hashear la contraseña
        hashed_password = pwd_context.hash(password)

        # 3) Crear perfil
        profile = {
            "email": payload.email,
            "display_name": payload.display_name,
            "role": payload.role,
            "disabled": False,
            "password": hashed_password,
        }

        uid = UserRepo.create(profile)  # genera ID en tu repo

        return UserResponse(
            uid=uid,
            email=payload.email,
            display_name=payload.display_name,
            role=payload.role,
            disabled=False,
        )

    @staticmethod
    def list_users(limit: int = 50) -> List[dict]:
        return UserRepo.list(limit)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def authenticate(email: str, password: str) -> Optional[dict]:
        user = UserRepo.get_by_email(email)
        if not user:
            return None
        if not UserService.verify_password(password, user["password"]):
            return None
        return user