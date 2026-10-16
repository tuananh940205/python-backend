from app.services.chat_service import ChatService
from app.services.user_service import UserService
from collections.abc import Generator
from sqlalchemy.orm import Session
from app.database import SessionLocal
# Quản lý Session bằng Dependency Injection

def get_user_service() -> UserService:
    return UserService()
def get_chat_service() -> ChatService:
    return ChatService()

# Khi một API cần truy cập database, FastAPI sẽ gọi get_db() thông qua Depends(get_db).
# Session được cung cấp cho API và đóng lại sau khi request hoàn tất.
# Cơ chế này gọi là Dependency Injection (DI).
# Bạn có thể hình dung tương tự việc ASP.NET Core inject một service vào Controller, thay vì tự tạo service mới ở mọi nơi.
# Điểm khác là get_db() ở đây trực tiếp quản lý vòng đời của SQLAlchemy Session.
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()