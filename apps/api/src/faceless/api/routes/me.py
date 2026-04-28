import uuid

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from faceless.api.deps import CurrentUser

router = APIRouter(prefix="/me", tags=["me"])


class MeResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    credit_balance: int


@router.get("", response_model=MeResponse)
async def get_me(user: CurrentUser) -> MeResponse:
    return MeResponse(id=user.id, email=user.email, credit_balance=user.credit_balance)
