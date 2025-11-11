from pydantic import BaseModel, EmailStr
from typing import Optional, Literal
from datetime import datetime

Role = Literal["superadmin", "admin", "user"]

class UserCreate(BaseModel):
    email: EmailStr
    display_name: str
    role: Role = "user"
    password: str


class UserResponse(BaseModel):
    uid: str
    email: EmailStr
    display_name: str
    role: Role
    disabled: bool = False
    created_at: Optional[datetime] = None 
