from sqlalchemy import Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

# User là một Python class ánh xạ tới bảng users.
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(always=True),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        # Tạo ràng buộc duy nhất
        unique=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    age: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    password_hash: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="user",
        server_default="user",
    )

# user = User(
#     name="An",
#     email="an@example.com",
#     age=30,
# )
# Đoạn code này mới tạo một đối tượng Python.
# Dữ liệu chưa được lưu vào PostgreSQL cho đến khi bạn thêm đối tượng vào session và commit transaction.
# Ngoài ra, khai báo Model không tự động sửa cấu trúc bảng đã tồn tại.
# Model phải khớp với schema thực tế trong database.