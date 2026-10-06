from fastapi import APIRouter, Depends
from application.commands.login_usuario import LoginUserHandler, LoginUserCommand
from  application.interfaces.auth_service import AuthService
from domain.entities.user import User
from infrastructure.api.v1.schemas.auth import LoginBody, RegisterBody
from infrastructure.api.v1.dependencies import get_auth_service, get_current_user
from application.commands.register_user import RegisterUserHandler, RegisterUserCommand

router = APIRouter(prefix="/auth")

@router.post("/register", status_code=201)
async def register(body: RegisterBody, auth: AuthService = Depends(get_auth_service)):
    user = await RegisterUserHandler(auth).handle(RegisterUserCommand(**body.model_dump()))
    return {"id": user.id, "email": user.email}

@router.post("/login")
async def login(body: LoginBody, auth: AuthService = Depends(get_auth_service)):
    s = await LoginUserHandler(auth).handle(LoginUserCommand(**body.model_dump()))
    return {"access_token": s.access_token, "refresh_token": s.refresh_token}

@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return user