from typing import Literal

from pydantic import BaseModel, EmailStr


class RegisterBody(BaseModel):
    email: EmailStr
    password: str
    role: Literal["user", "repartidor"] = "user"


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    role: str = "user"
