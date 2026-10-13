from sqlalchemy.orm import Session

from app.models import User
from app.repositories import user_repository
from app.schemas import UserUpdate
from app.schemas.user import UserCreate, UserResponse

# UserNotFoundError là lỗi nghiệp vụ do ứng dụng định nghĩa.
# Service không cần import HTTPException của FastAPI.
# Nhờ đó, bạn có thể tái sử dụng service trong script, tác vụ nền hoặc các giao diện khác.
class UserNotFoundError(Exception):
    pass

def list_users(db: Session) -> list[User]:
    return user_repository.get_all(db)

def get_user(db: Session, user_id: int) -> User:
    user = user_repository.get_by_id(db, user_id)

    if user is None:
        raise UserNotFoundError(f"User {user_id} not found")

    return user

def create_user(db: Session, payload: UserCreate) -> User:
    user = User(**payload.model_dump())

    try:
        user_repository.add(db, user)
        # db.commit() xác nhận transaction.
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        # Khi có lỗi trong quá trình ghi dữ liệu, db.rollback() hoàn tác những thay đổi chưa commit của transaction đó.
        db.rollback()
        raise


def update_user(db: Session, user_id: int, payload: UserUpdate) -> User:
    user = get_user(db, user_id)
    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise ValueError("No fields provided")

    if any(
        key in changes and changes[key] is None
        for key in ("name", "email")
    ):
        raise ValueError("name and email cannot be null")

    try:
        for field, value in changes.items():
            setattr(user, field, value)

        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise

def delete_user(db: Session, user_id: int) -> None:
    user = get_user(db, user_id)

    try:
        user_repository.delete(db, user)
        db.commit()
    except Exception:
        db.rollback()
        raise

class UserService:
    def create_user(self, user: UserCreate) -> UserResponse:
        return UserResponse(
            id = 1,
            name = user.name,
            age = user.age,
        )
    # Giả lập
    # Sau này: Service -> Repository -> PostgreSQL
    def get_user(self, user_id: int) -> UserResponse:
        return UserResponse(
            id = user_id,
            name = "Tuan",
            age = 30,
        )
    def delete_user(self, user_id: int):
        print(f"Delete user {user_id}")