from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator

# giới hạn dữ liệu client được gửi khi tạo user.
class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    age: int | None = Field(default=None, ge=0, le=150)

    @field_validator("name")
    @classmethod
    # loại bỏ khoảng trắng ở đầu và cuối tên.
    def normalize_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Name cannot be blank")

        return value


# cho phép cập nhật một số trường mà không bắt buộc gửi toàn bộ dữ liệu.
class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    age: int | None = Field(default=None, ge=0, le=150)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return value

        value = value.strip()

        if not value:
            raise ValueError("Name cannot be blank")

        return value

# định nghĩa cấu trúc JSON trả về client, bao gồm id do database tạo ra.
class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    age: int | None
    role: str

# ConfigDict(from_attributes=True) cho phép Pydantic đọc giá trị từ thuộc tính của đối tượng SQLAlchemy.
# Lưu ý: age không có giá trị mặc định trong UserRead, nên trường này phải tồn tại trong đối tượng trả về, dù giá trị có thể là None.

__all__ = ["UserCreate", "UserRead", "UserUpdate"]
