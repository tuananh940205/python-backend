"""
EXAMPLE: FastAPI Router với Repository Pattern
Đây là ví dụ hoàn chỉnh của cách sử dụng UserRepository trong API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.repositories.user_repository import UserRepository
from pydantic import BaseModel, EmailStr
from typing import List

# ==================== PYDANTIC MODELS (Schemas) ====================

class UserCreate(BaseModel):
    """Schema cho request tạo user"""
    name: str
    email: EmailStr
    username: str
    is_active: bool = True

class UserUpdate(BaseModel):
    """Schema cho request cập nhật user"""
    name: str | None = None
    email: EmailStr | None = None
    username: str | None = None
    is_active: bool | None = None

class UserResponse(BaseModel):
    """Schema cho response trả về user"""
    id: int
    name: str
    email: str
    username: str
    is_active: bool

    class Config:
        from_attributes = True

# ==================== DEPENDENCIES ====================

def get_db():
    """Dependency để lấy database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== ROUTER ====================

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

# CREATE - POST /users
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Tạo user mới
    - Kiểm tra email chưa tồn tại
    - Kiểm tra username chưa tồn tại
    """
    repo = UserRepository(db)

    # Kiểm tra email đã tồn tại
    if repo.get_by_email(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    # Kiểm tra username đã tồn tại
    if repo.get_by_username(user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Tạo user mới
    return repo.create(user.model_dump())

# READ BY ID - GET /users/1
@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Lấy user theo ID"""
    repo = UserRepository(db)
    user = repo.read_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user

# READ ALL - GET /users
@router.get("/", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách users (có pagination)

    Query params:
    - skip: số records cần bỏ qua (default: 0)
    - limit: số records cần lấy (default: 10)
    """
    repo = UserRepository(db)
    return repo.read_all(skip=skip, limit=limit)

# LIST ACTIVE USERS - GET /users/active
@router.get("/active", response_model=List[UserResponse])
def list_active_users(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Lấy danh sách users hoạt động (is_active=true)"""
    repo = UserRepository(db)
    return repo.get_active_users(skip=skip, limit=limit)

# SEARCH - GET /users/search/john
@router.get("/search/{keyword}", response_model=List[UserResponse])
def search_users(keyword: str, db: Session = Depends(get_db)):
    """
    Tìm users theo từ khóa
    - Tìm theo tên hoặc email (case-insensitive)

    Example: GET /users/search/john
    """
    repo = UserRepository(db)
    users = repo.search_users(keyword)

    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No users found matching '{keyword}'"
        )

    return users

# SEARCH BY ROLE - GET /users/role/admin
@router.get("/role/{role}", response_model=List[UserResponse])
def get_users_by_role(
    role: str,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Lấy users theo role"""
    repo = UserRepository(db)
    return repo.get_users_by_role(role, skip=skip, limit=limit)

# UPDATE - PUT /users/1
@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db)
):
    """
    Cập nhật user
    - Chỉ cập nhật các field được gửi
    """
    repo = UserRepository(db)

    # Kiểm tra user tồn tại
    existing_user = repo.read_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Nếu cập nhật email, kiểm tra email mới chưa dùng
    if user.email and user.email != existing_user.email:
        if repo.get_by_email(user.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )

    # Cập nhật user
    update_data = user.model_dump(exclude_unset=True)
    return repo.update(user_id, update_data)

# DELETE - DELETE /users/1
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Xóa user"""
    repo = UserRepository(db)

    if not repo.delete(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

# STATISTICS - GET /users/stats
@router.get("/stats", response_model=dict)
def get_user_stats(db: Session = Depends(get_db)):
    """Lấy thống kê về users"""
    repo = UserRepository(db)

    total = repo.count_users()
    active = repo.count_active_users()

    return {
        "total_users": total,
        "active_users": active,
        "inactive_users": total - active
    }

# ==================== CÁCH SỬ DỤNG ====================
"""
1. Import router trong app/main.py:
   from app.routers.users import router
   app.include_router(router)

2. Test API:

   # CREATE
   curl -X POST "http://localhost:8000/users/" \
     -H "Content-Type: application/json" \
     -d '{"name":"John Doe","email":"john@example.com","username":"johndoe"}'

   # READ
   curl "http://localhost:8000/users/1"

   # LIST
   curl "http://localhost:8000/users/?skip=0&limit=10"

   # SEARCH
   curl "http://localhost:8000/users/search/john"

   # LIST BY ROLE
   curl "http://localhost:8000/users/role/admin?skip=0&limit=10"

   # UPDATE
   curl -X PUT "http://localhost:8000/users/1" \
     -H "Content-Type: application/json" \
     -d '{"name":"Jane Doe"}'

   # DELETE
   curl -X DELETE "http://localhost:8000/users/1"

   # STATS
   curl "http://localhost:8000/users/stats"
"""
