from fastapi import Depends, HTTPException, status
from app.auth_dependencies import get_current_user
from app.models import User

def require_role(*allowed_roles: str):
    def check_role(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )

        return current_user

    return check_role

def require_self_or_admin(
    resource_user_id: int,
    current_user: User,
) -> None:
    if (
        current_user.id == resource_user_id
        and current_user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access another user's resource",
        )