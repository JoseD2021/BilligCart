from fastapi import APIRouter, Depends

from src.application.commands.auth.login_user import LoginUserCommand, LoginUserHandler
from src.application.commands.auth.register_user import (
    RegisterUserCommand,
    RegisterUserHandler,
)
from src.domain.entities.user import User
from src.infrastructure.api.v1.dependencies import (
    get_current_user,
    get_login_handler,
    get_register_handler,
)
from src.infrastructure.api.v1.schemas.auth import LoginBody, RegisterBody

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", status_code=201)
async def register(body: RegisterBody, handler: RegisterUserHandler = Depends(get_register_handler),):
    result = await handler.handle(RegisterUserCommand(**body.model_dump()))
    response = {"id": result.user.id, "email": result.user.email, "role": result.user.role}
    if result.session is not None:
        response["access_token"] = result.session.access_token
        response["refresh_token"] = result.session.refresh_token
    return response

@router.post("/login")
async def login(body: LoginBody, handler: LoginUserHandler = Depends(get_login_handler)):
    s = await handler.handle(LoginUserCommand(**body.model_dump()))
    return {"access_token": s.access_token, "refresh_token": s.refresh_token}

@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return user