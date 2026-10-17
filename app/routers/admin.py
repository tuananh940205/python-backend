from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.authorization import require_role
from app.dependencies import get_db
from app.models import User
from app.schemas import UserRead

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users", response_model=list[UserRead])
def list_all_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    statement = select(User).order_by(User.id)
    return list(db.scalars(statement).all())