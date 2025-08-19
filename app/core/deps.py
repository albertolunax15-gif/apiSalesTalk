from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt, ExpiredSignatureError
from datetime import datetime, timezone

# importar la misma configuración desde security.py
from .security import SECRET_KEY, ALGORITHM

security = HTTPBearer(auto_error=True)  # forzar comportamiento en Swagger (candado)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token requerido",
                            headers={"WWW-Authenticate": "Bearer"})

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        uid: str = payload.get("uid")
        exp: int = payload.get("exp")

        if not email or not role:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Token inválido: falta información (sub o role)",
                                headers={"WWW-Authenticate": "Bearer"})

        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(tz=timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Token expirado",
                                headers={"WWW-Authenticate": "Bearer"})

        return {"uid": uid, "email": email, "role": role}

    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token expirado",
                            headers={"WWW-Authenticate": "Bearer"})
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=f"Token inválido o expirado ({str(e)})",
                            headers={"WWW-Authenticate": "Bearer"})


def require_role(role: str):
    def checker(user: dict = Depends(get_current_user)):
        if user.get("role") != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="No tienes permisos para esta acción")
        return user
    return checker