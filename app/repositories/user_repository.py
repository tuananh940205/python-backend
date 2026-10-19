from sqlalchemy import select
# Repository chỉ chịu trách nhiệm làm việc với dữ liệu.
# Nó không cần biết request đến từ trình duyệt, ứng dụng mobile hay một service khác.
from sqlalchemy.orm import Session

from app.models import User


def get_by_id(db: Session, user_id: int):
    return db.get(User, user_id)

def get_all(db: Session) -> list[User]:
    statement = select(User).order_by(User.id)
    return list(db.scalars(statement).all())

def add(db: Session, user: User) -> User:
    db.add(user)
    return user

def delete(db: Session, user: User) -> None:
    db.delete(user)