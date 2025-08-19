from fastapi import HTTPException, status
from ..core.security import create_access_token
from ..repositories.user_repo import UserRepo
from ..core.security import ACCESS_TOKEN_EXPIRE_MINUTES

class AuthService:
    @staticmethod
    def login(email: str, password: str) -> str:
        # Tu repositorio debe devolver user con keys: email, role, uid, password_hash
        user = UserRepo.get_by_email(email)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

        # verifica contraseña: asumo que ya tienes verify_password somewhere,
        # si usas passlib: pwd_context.verify(password, user["password"])
        from ..core.security import SECRET_KEY  # solo por visibilidad, no necesario aquí
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        if "password" not in user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario sin contraseña")
        if not pwd.verify(password, user["password"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

        # genera token con los claims que deps.py espera
        token = create_access_token(sub=user["email"], role=user.get("role", "user"), uid=user.get("uid", ""))
        return token

    @staticmethod
    def verify_token(token: str) -> dict:
        # útil si quieres chequear token manualmente en algún lugar
        from jose import jwt
        from ..core.security import SECRET_KEY, ALGORITHM
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])