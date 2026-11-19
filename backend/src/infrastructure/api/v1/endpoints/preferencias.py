from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from src.infrastructure.api.v1.dependencies import (
    get_current_user,
    get_preferences_use_case,
)

router = APIRouter(prefix="/preferencias", tags=["Preferencias"])


class PreferencesBody(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    restricciones: list[str] = Field(default_factory=list, max_length=30)
    presupuesto_semanal: float = 0


@router.get("")
async def get_preferences(user=Depends(get_current_user), use_case=Depends(get_preferences_use_case)):
    return await use_case.get(user.id)


@router.put("")
async def save_preferences(body: PreferencesBody, user=Depends(get_current_user), use_case=Depends(get_preferences_use_case)):
    return await use_case.save(user.id, **body.model_dump())
