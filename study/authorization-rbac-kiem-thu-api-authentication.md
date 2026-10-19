
<p align="center" style="font-size: 30px">
    <b>
        Authorization, RBAC và kiểm thử API Authentication
    </b>
</p>

Ở bài trước, bạn đã xây dựng luồng đăng ký, đăng nhập, hash mật khẩu và JWT access token.  
Bây giờ chúng ta sẽ phát triển hệ thống tài khoản theo hướng gần với backend thực tế hơn.

Mục tiêu của bài này:
1. Phân biệt người dùng đã đăng nhập với người dùng có quyền thực hiện hành động.
2. Triển khai RBAC — phân quyền theo vai trò.
3. Bổ sung quyền sở hữu tài nguyên, ví dụ chỉ sửa hồ sơ của chính mình.
4. Viết API Test bằng pytest và FastAPI TestClient.

# 1. Authentication khác Authorization như thế nào?

- `Authentication`: xác minh bạn là ai, ví dụ xác minh JWT và tìm user trong database.
- `Authorization`: xác định bạn được phép làm gì sau khi đã xác thực.

Ví dụ, hệ thống có ba vai trò:
Vai trò | Quyền hạn
|-|-|
User | Xem hồ sơ của mình, cập nhật thông tin của mình.
Moderator | Có quyền bổ sung để thực hiện một số thao tác quản lý nội dung.
Admin | Được phép quản lý tài khoản và thực hiện các thao tác quản trị.

Chúng ta sẽ triển khai một ví dụ đơn giản với hai vai trò `user` và `admin`.  
Vai trò `moderator` có thể được bổ sung sau khi bạn hiểu cơ chế.

Một nguyên tắc quan trọng: không lấy vai trò do client tự gửi lên để quyết định quyền truy cập.  
Quyền phải được lấy từ nguồn dữ liệu đáng tin cậy ở server.

# 2. Thêm trường `role` vào PostgreSQL

Mở pgAdmin, chọn database `backend_learning`, chạy SQL:
```sql
ALTER TABLE users
ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user';

ALTER TABLE users
ADD CONSTRAINT ck_users_role
CHECK (role IN ('user', 'admin'))
```

Nếu constraint hoặc cột `role` đã tồn tại, không chạy lại nguyên xi. Hãy kiểm tra cấu trúc bảng trước.

Lúc này, tài khoản mới mặc định có role `user`.  
Tài khoản `admin` chỉ nên được cấp bởi quy trình quản trị đáng tin cậy, không phải bởi API đăng ký công khai.

Để tạo một tài khoản admin thử nghiệm, sau khi đã đăng ký tài khoản bằng API, bạn có thể chạy:
```sql
UPDATE users
SET role = 'admin'
WHERE email = 'an@example.com'
```
Thay email bằng tài khoản thử nghiệm của bạn. Không sử dụng cách cập nhật trực tiếp này làm quy trình cấp quyền trong môi trường production.

# 3. Cập nhật SQLAlchemy Model
Trong `app/models.py`, bổ sung trường role vào class User:
```py
role: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default="user",
    server_default="user",
)
```
`default="user"` áp dụng ở phía SQLAlchemy; server_default="user" giúp database cũng có giá trị mặc định khi một thao tác insert không cung cấp trường này.

Thêm role vào `UserRead` trong `app/schemas.py`:
```py
class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    age: int | None
    role: str
```
Từ giờ API trả thông tin user sẽ có thêm trường role.  
Đừng thêm trường `role` vào `RegisterRequest`: người đăng ký công khai không được tự chọn mình là admin.

# 4. Tạo dependency kiểm tra quyền
Tạo file mới `app/authorization.py`:
```py

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
```

Cách dùng:
```py
Depends(require_role("admin"))
```
FastAPI sẽ:
1. Chạy get_current_user() để xác thực token.
2. Lấy user tương ứng từ database.
3. Kiểm tra role.
4. Cho phép request tiếp tục nếu vai trò hợp lệ; nếu không, trả 403 Forbidden.

Phân biệt hai loại lỗi:
- 401 Unauthorized: chưa xác thực hoặc token không hợp lệ.
- 403 Forbidden: đã xác thực nhưng không đủ quyền.
Tên HTTP 401 dễ gây nhầm, nhưng đây là cách sử dụng thông thường của HTTP API.

# 5. Tạo API chỉ admin mới được gọi
Tạo file `app/routers/admin.py`:
```py

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.authorization import require_role
from app.dependencies import get_db
from app.models import User
from app.schemas import UserRead

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users", response_model=list[UserRead])
def list_all_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    statement = select(User).order_by(User.id)
    return list(db.scalars(statement).all())
```

Sau đó đăng ký router trong `app/main.py`:
```py
from app.routers.admin import router as admin_router
...
app.include_router(admin_router)
```
Giờ endpoint `GET /admin/users` chỉ cho tài khoản có role `admin` truy cập.  
Tại sao không đặt role trực tiếp trong JWT rồi chỉ kiểm tra token?  
Bạn có thể đưa role vào JWT, nhưng khi quyền của user bị thay đổi thì token cũ có thể vẫn giữ role cũ cho đến khi hết hạn.  
Ví dụ này đọc role từ database mỗi request để quyền được cập nhật ngay khi dữ liệu thay đổi, đổi lại sẽ cần truy cập database.

# 6. Bảo vệ tài nguyên theo quyền sở hữu
`RBAC` chưa đủ trong nhiều ứng dụng.  
Một user có role `user` không nên được sửa hồ sơ của `user` khác chỉ vì họ đã đăng nhập.
Bạn có thể dùng `helper` sau trong `app/authorization.py`:
```py
def require_self_or_admin(
    resource_user_id: int,
    current_user: User,
) -> None:
    if (
        current_user.id != resource_user_id
        and current_user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot access another user's resource",
        )
```

Ví dụ, trong endpoint cập nhật hồ sơ, sau khi tìm thấy user cần sửa:
```py
current_user = ...  # Lấy qua Depends(get_current_user)

require_self_or_admin(user_id, current_user)

# Chỉ sau bước kiểm tra quyền mới thực hiện cập nhật
```
Đoạn helper trên minh họa quy tắc quyền sở hữu; khi tích hợp, cần inject current_user bằng Depends(get_current_user) và đặt kiểm tra quyền trước mọi thao tác ghi dữ liệu.

Luồng xử lý đúng là:
1. Xác thực token.
2. Tìm tài nguyên.
3. Kiểm tra user có quyền truy cập tài nguyên đó hay không.
4. Thực hiện thao tác nếu được phép.

Không nên chỉ ẩn nút sửa ở giao diện frontend.  
Server luôn phải kiểm tra quyền, vì client có thể tự gửi request.

# 7. Viết API Test cho RBAC

Chúng ta sẽ kiểm thử `GET /admin/users` mà không cần đăng nhập thật hoặc kết nối `PostgreSQL`.  
Test sẽ override dependency lấy user hiện tại, để tập trung vào việc kiểm tra quyền.

Cài thêm thư viện test nếu cần:
```powershell
pip install httpx
```
Tạo file `tests/test_authorization.py`:
```py
from fastapi.testclient import TestClient

from app.main import app
from app.auth_dependencies import get_current_user
from app.models import User


def make_user(user_id: int, role: str) -> User:
    return User(
        id=user_id,
        name="Test User",
        email="test@example.com",
        age=30,
        role=role,
    )

def test_admin_can_access_admin_endpoint():
    app.dependency_overrides[get_current_user] = (
        lambda: make_user(1, "admin")
    )

    try:
        client = TestClient(app)
        response = client.get("/admin/users")

        # Endpoint còn cần database để lấy danh sách.
        # Test quyền nên tách phần kiểm tra role khỏi truy vấn DB.
        assert response.status_code != 403
    finally:
        app.dependency_overrides.clear()

def test_regular_user_is_forbidden():
    app.dependency_overrides[get_current_user] = (
        lambda: make_user(2, "user")
    )

    try:
        client = TestClient(app)
        response = client.get("/admin/users")

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
```

Test đầu tiên ở trên vẫn có thể gặp lỗi database, vì endpoint admin thực sự truy vấn danh sách user.  
Để có một unit test hoàn toàn độc lập với database, tốt hơn là kiểm tra dependency require_role() trực tiếp bằng endpoint test nhỏ hoặc mock thêm get_db.

Một lựa chọn đơn giản, đáng tin cậy hơn cho bài học này là kiểm tra dependency quyền bằng endpoint test chuyên dụng.

Tạo file `tests/test_role_dependency.py`:
```py
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth_dependencies import get_current_user
from app.authorization import require_role
from app.models import User

test_app = FastAPI()

@test_app.get("/admin-only")
def admin_only(
    user: User = Depends(require_role("admin")),
):
    return {"message": "welcome admin"}

def make_user(role: str) -> User:
    return User(
        id=1,
        name="Test User",
        email="test@example.com",
        age=30,
        role=role,
    )

def test_admin_is_allowed():
    test_app.dependency_overrides[get_current_user] = (
        lambda: make_user("admin")
    )

    try:
        response = TestClient(test_app).get("/admin-only")
        assert response.status_code == 200
        assert response.json() == {"message": "welcome admin"}
    finally:
        test_app.dependency_overrides.clear()


def test_user_is_forbidden():
    test_app.dependency_overrides[get_current_user] = (
        lambda: make_user("user")
    )

    try:
        response = TestClient(test_app).get("/admin-only")
        assert response.status_code == 403
    finally:
        test_app.dependency_overrides.clear()
```
Test thứ hai tập trung đúng vào logic phân quyền.  
Nó không cần PostgreSQL vì endpoint test không truy vấn dữ liệu và dependency xác thực được thay bằng một user giả.

Chạy test từ thư mục gốc project:
```powershell
python -m pytest tests/test_role_dependency.py -v
```
Kết quả
```bash
(.venv) PS D:\projects\python\python-backend> python -m pytest tests/test_role_dependency.py -v
================================================= test session starts =================================================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.7.0 -- D:\projects\python\python-backend\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\projects\python\python-backend
configfile: pyproject.toml
plugins: anyio-4.15.1
collected 2 items

tests/test_role_dependency.py::test_admin_is_allowed PASSED                                                      [ 50%]
tests/test_role_dependency.py::test_user_is_forbidden PASSED                                                     [100%]

================================================== warnings summary ===================================================
.venv\Lib\site-packages\fastapi\testclient.py:1
  D:\projects\python\python-backend\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

.venv\Lib\site-packages\fastapi\applications.py:1196
  D:\projects\python\python-backend\.venv\Lib\site-packages\fastapi\applications.py:1196: PytestCollectionWarning: cannot collect 'test_app' because it is not a function.
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
============================================ 2 passed, 2 warnings in 0.78s ============================================
```

# 9. Tổng kết
Bạn đã học được ba lớp bảo vệ:
- JWT: xác minh danh tính người gọi.
- RBAC: kiểm tra vai trò có được phép thực hiện hành động hay không.
- Ownership check: kiểm tra người gọi có quyền truy cập tài nguyên cụ thể hay không.

Một lưu ý khi triển khai thực tế: dùng Alembic để quản lý thay đổi schema, tránh cấp quyền admin qua endpoint đăng ký công khai, và kiểm tra quyền ở phía server cho mọi thao tác nhạy cảm.