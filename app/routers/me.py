from fastapi import APIRouter, Depends

from app.auth_dependencies import get_current_user
from app.models import User
from app.schemas import UserRead

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

@router.get("/me", response_model=UserRead)
def read_my_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user