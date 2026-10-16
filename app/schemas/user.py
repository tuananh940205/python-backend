from pydantic import BaseModel, Field

# Dùng cho POST /users
# client gửi { "name": "Tuan", "age": 30 }
class UserCreate(BaseModel):
    # Kí tự tối thiểu: 2, max: 50
    name: str = Field(min_length=2, max_length=50)
    # value min = 18, max - 100
    # Có thể tự parse nếu age = "18"
    age: int = Field(ge=18, le=100)
# Dùng cho response
class UserResponse(BaseModel):
    id: int
    name: str
    age: int