# from fastapi import APIRouter, Depends, HTTPException, status
# from app.schemas.user import UserResponse, UserCreate
# from app.services.user_service import UserService
# from app.dependencies import get_user_service
#
# # Get
# router = APIRouter(
#     # `prefix` là tiền tố được ghép vào đầu đường dẫn của mọi endpoint trong router này.
#     # Với `prefix="/users"` và các decorator bên dưới dùng `"/"`, endpoint có đường dẫn `/users/`.
#     # Nếu đổi thành `prefix="/api/users"`, các endpoint sẽ thành `/api/users/`.
#     # Nếu bỏ prefix (`prefix=""`), các endpoint dùng `"/"` sẽ nằm ở đường dẫn gốc `/`.
#     prefix="/users",
#     # `tags` là nhãn để nhóm endpoint trong tài liệu OpenAPI/Swagger (`/docs`); nó không đổi URL
#     # và cũng không tạo cơ chế phân quyền. Có thể đổi thành `["user-management"]` để đổi tên nhóm,
#     # hoặc dùng `["users", "accounts"]` để endpoint xuất hiện trong cả hai nhóm.
#     tags=["users"],
# )
#
# # response phải theo cấu trúc của UserResponse
# # Nếu chỉ định status code, sử dụng logic @router.post("/", response_model=UserResponse, status_code=201)
# @router.post("/", response_model=UserResponse, status_code = status.HTTP_201_CREATED)
# def create_user(user: UserCreate, service: UserService = Depends(get_user_service)) -> UserResponse:
#     # return user_service.create_user(user)
#     # Gọi `get_user_uservice()` và trả kết quả vào biến `service`
#     return service.create_user(user)
#
# @router.get("/", response_model=UserResponse)
# def get_users(user_id: int, service: UserService = Depends(get_user_service)) -> UserResponse:
#     # return user_service.get_user(user_id)
#     if user_id != 1:
#         raise HTTPException(
#             status_code = 404,
#             detail = "User not found",
#         )
#     return service.get_user(user_id)
#
# @router.delete("/{user_id}", status_code = status.HTTP_204_NO_CONTENT)
# def delete_user(user_id: int, service: UserService = Depends(get_user_service)):
#     service.delete_user(user_id)


from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import User
from app.schemas import UserCreate, UserRead, UserUpdate
from app.services import user_service
from app.services.user_service import UserNotFoundError, DuplicateUserDataError

router = APIRouter(prefix="/users", tags=["Users"])

def to_not_found(error: UserNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=str(error),
    )

# READ: lấy danh sách user
@router.get("/", response_model=list[UserRead])
def get_users(db: Session = Depends(get_db)):
    # return old_get_users(db)
    return user_service.list_users(db)

def old_get_users(db: Session):
    # select(User) tạo câu truy vấn SQLAlchemy để lấy các đố i tượng User.
    # Khi thực thi, SQLAlchemy tạo SQL tương đương:
    # SELECT id, name, email, age
    # FROM users
    # ORDER BY id;
    statement = select(User).order_by(User.id)
    return db.scalars(statement).all()


# READ: lấy một user
@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    # return old_get_users(db, user_id)
    try:
        return user_service.get_user(db, user_id)
    except UserNotFoundError as error:
        raise to_not_found(error) from error

def old_get_user(db: Session, user_id: int):
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user

# CREATE: tạo user
@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    # return old_create_user(payload, db)
    try:
        return user_service.create_user(db, payload)
    except DuplicateUserDataError as error:
        raise HTTPException(
            status_code=status.http_409_CONFLICT,
            detail=str(error),
        ) from error

def old_create_user(payload: UserCreate, db: Session):
    user = User(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)

    return user

# UPDATE: cập nhật một phần dữ liệu
@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
):
    # return old_update_user(user_id, payload, db)
    try:
        return user_service.update_user(db, user_id, payload)
    except UserNotFoundError as error:
        raise to_not_found(error) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

def old_update_user(user_id: int, payload: UserUpdate, db: Session):
    # model_dump() chuyển Pydantic object thành dictionary.
    # User(**...) truyền các trường dictionary vào constructor.
    # db.add() đánh dấu đối tượng để lưu trong session.
    # db.commit() xác nhận transaction, ghi thay đổi vào database.
    # db.refresh() đọc lại dữ liệu từ database, chẳng hạn id vừa được sinh ra.
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Nếu client chỉ gửi: { "age": 31 } thì changes chỉ chứa age, không ghi đè các trường khác.
    # Đây là lý do chúng ta dùng PATCH thay vì bắt buộc cập nhật toàn bộ đối tượng.
    changes = payload.model_dump(exclude_unset=True)

    # Nếu không tìm thấy user, API trả HTTP 404 Not Found.
    # Nếu input không hợp lệ theo Pydantic, FastAPI tự trả lỗi 422 Unprocessable Entity.
    # Trong ứng dụng thực tế, bạn cũng cần xử lý lỗi database và rollback session khi transaction thất bại;
    # phần đó sẽ được mở rộng sau.
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided",
        )

    if any(
            key in changes and changes[key] is None
            for key in ("name", "email")
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="name and email cannot be null",
        )

    for field, value in changes.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return user


# DELETE: xóa user
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    # return old_delete_user(user_id, db)
    try:
        user_service.delete_user(db, user_id)
    except UserNotFoundError as error:
        raise to_not_found(error) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)

def old_delete_user(user_id: int, db: Session):
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    db.delete(user)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)