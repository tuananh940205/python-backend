from fastapi import APIRouter, Depends, HTTPException
from app.schemas.user import UserResponse, UserCreate
from app.services.user_service import UserService
from app.dependencies import get_user_service

# Get
router = APIRouter(
    # `prefix` là tiền tố được ghép vào đầu đường dẫn của mọi endpoint trong router này.
    # Với `prefix="/users"` và các decorator bên dưới dùng `"/"`, endpoint có đường dẫn `/users/`.
    # Nếu đổi thành `prefix="/api/users"`, các endpoint sẽ thành `/api/users/`.
    # Nếu bỏ prefix (`prefix=""`), các endpoint dùng `"/"` sẽ nằm ở đường dẫn gốc `/`.
    prefix="/users",
    # `tags` là nhãn để nhóm endpoint trong tài liệu OpenAPI/Swagger (`/docs`); nó không đổi URL
    # và cũng không tạo cơ chế phân quyền. Có thể đổi thành `["user-management"]` để đổi tên nhóm,
    # hoặc dùng `["users", "accounts"]` để endpoint xuất hiện trong cả hai nhóm.
    tags=["users"],
)

# response phải theo cấu trúc của UserResponse
@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate, service: UserService = Depends(get_user_service)) -> UserResponse:
    # return user_service.create_user(user)
    # Gọi `get_user_uservice()` và trả kết quả vào biến `service`
    return service.create_user(user)

@router.get("/", response_model=UserResponse)
def get_users(user_id: int, service: UserService = Depends(get_user_service)) -> UserResponse:
    # return user_service.get_user(user_id)
    if user_id != 1:
        raise HTTPException(
            status_code = 404,
            detail = "User not found",
        )
    return service.get_user(user_id)