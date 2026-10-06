from pydantic import BaseModel, EmailStr

class RegisterBody(BaseModel):
    email: EmailStr
    password: str
    
class LoginBody(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str