<p align="center" style="font-size: 30px">
    <b>Authentication và Authorization trong FastAPI</b>
</p>

Sau bài này, bạn sẽ có thể:
- Đăng ký tài khoản và lưu mật khẩu an toàn.
- Đăng nhập bằng email và mật khẩu.
- Phát hành JWT access token.
- Yêu cầu token khi gọi API riêng tư.
- Phân biệt Authentication và Authorization.

## 1. Phân biệt Authentication và Authorization

```
Authentication — Xác thực
Bạn là ai?
Ví dụ: người dùng gửi email và mật khẩu để đăng nhập. Server xác minh thông tin và cấp token nếu hợp lệ.


Authorization — Phân quyền
Bạn được phép làm gì?
Ví dụ: người dùng đã đăng nhập chỉ được sửa hồ sơ của mình, không được sửa hồ sơ người khác.
```
JWT giúp server xác minh danh tính và một số thông tin được cấp trong token.  
Tuy nhiên, có token hợp lệ không có nghĩa là được phép thực hiện mọi hành động.

## 2. Luồng đăng ký và đăng nhập

```
                    1. Client
              Gửi Email và mật khẩu
                        ↓
                   2. FastAPI
        Kiểm tra input, xác minh thông tin
                        ↓
                 3. PostgreSQL
Lưu email và password hash, không lưu mật khẩu gốc
                        ↓
              4. JWT access token
       Client dùng token để gọi API được bảo vệ
```
Một nguyên tắc bảo mật quan trọng: không lưu mật khẩu dạng văn bản thuần (plain text), và không tự viết thuật toán hash mật khẩu.  
Chúng ta sẽ sử dụng thư viện được thiết kế cho mục đích này.

## 3. Cài thư viện bảo mật

Trong PowerShell, tại thư mục gốc project và đã kích hoạt `.venv`, chạy:
```powershell
pip install "pwdlib[argon2]" PyJWT python-multipart
```
Các thư viện này có vai trò:
- `pwdlib[argon2]`: hash và xác minh mật khẩu bằng `Argon2`
- `PyJWT`: Tạo và xác minh JWT
- `python-multipart`: Xử lý dữ liệu form mà endpoint đăng nhập sử dụng

## 4. Chuẩn bị database

Bảng `users` của bạn đã tồn tại, nhưng hiện chưa có trường lưu password hash.  
Trước tiên, kiểm tra email có bị trùng không
```SQL
SELECT email, COUNT(*)
FROM users
GROUP BY email
HAVING COUNT(*) > 1;
```
Nếu kết quả không có dòng nào, bạn có thể thêm ràng buộc email duy nhất và trường mật khẩu:
```SQL
ALTER TABLE users
ADD COLUMN password_hash VARCHAR(255);

ALTER TABLE users
ADD CONSTRAINT uq_user_email UNIQUE(email);
```

Nếu đã tồn tại constraint duy nhất cho email thì không nên thêm lại.  
Nếu truy vấn kiểm tra cho thấy email bị trùng, hãy xử lí dữ liệu trước khi lên constraint

Lưu ý: `password_hash` đang cho phép `NULL` để không làm hỏng các bản ghi cũ đã có trong bảng.  
Các tài khoản cũ chưa có password hash sẽ không thể đăng nhập bằng luồng mới cho đến khi được cấp lại mật khẩu.

## 5. Cập nhật SQLAlchemy Model

Trong `app/models.py`, giữ nguyên các trường đang có và cập nhật phần `email`, bổ sung `password_hash`:
```py
email: Mapped[str] = mapped_column(
    String(255),
    nullable=False,
    unique=True,
)

password_hash: Mapped[str | None] = mapped_column(
    String(255),
    nullable=True,
)
```

Các dòng trên phải nằm bên trong class `User`.  
`unique=True` mô tả constraint trong metadata của SQLALchemy; nó không tự thêm constraint vào bảng đã tồn tại.  
Vì vậy, chúng ta đã thêm constraint bằng SQL ở bước trước.

Trong dự án thực tế, nên đưa thay đổi schema này vào migration Alembic để có lịch sử thay đổi và triển khai nhất quán giữa các môi trường

## 6. Tạo schema cho đăng ký và token
Tạo file `app/auth_schemas.py`:
```py
from pydantic import BaseModel, EmailStr, Field

class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```
Chúng ta không trả `password_hash` trong response.  
Password hash chỉ được dùng nội bộ ở server.

Trong bài học này, mật khẩu có độ dài tối thiểu 8 ký tự.  
Khi xây dựng hệ thống thật, bạn cần bổ sung chính sách mật khẩu và bảo vệ chống thử đăng nhập liên tục.

## 7. Cấu hình JWT và hash mật khẩu

### 7.1 Thêm secret vào `.env`
Tạo secret ngẫu nhiên trong Powershell:
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
Ví dụ
```
nInggZSPc3y2QnLB12aCrdY-yaVmpYfIrcCXOnFi_a0
```

Copy kết quả vào .env:
```
JWT_SECRET_KEY=THAY_BANG_SECRET_VUA_TAO
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Không chia sẻ secret này và không commit .env lên Git.

### 7.2. Tạo app/security.py
```py
import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY chưa được cấu hình")

ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(" ", "30")
)

password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)

def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "exp": expires_at,
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
```

Giải thích:
- hash_password(str): chuyển mật khẩu thành hash an toàn để lưu trong database.
- verify_password(str): kiểm tra mật khẩu người dùng nhập có khớp hash hay không.
- create_access_token(): tạo JWT chứa sub (ID người dùng) và exp (thời điểm hết hạn).

JWT được ký để server phát hiện nội dung bị sửa đổi.  
JWT không tự mã hóa payload, nên không đưa mật khẩu và dữ liệu bí mật vào payload.

## 8. Tạo API đăng ký và đăng nhập
Tạo file `app/routers/auth.py`:
```py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth_schemas import RegisterRequest, TokenResponse
from app.dependencies import get_db
from app.models import User
from app.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = User(
        name=payload.name.strip(),
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
    )

    if not user.name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name cannot be blank",
        )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email may already be registered",
        ) from error

    return {"id": user.id, "name": user.name, "email": user.email}

@router.post("/login", response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    email = form.username.strip().lower()

    user = db.query(User).filter(User.email == email).first()

    if (
        user is None
        or user.password_hash is None
        or not verify_password(form.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}
```

Trong API đăng nhập, OAuth2PasswordRequestForm sử dụng trường username theo chuẩn OAuth2. Với ứng dụng của chúng ta, bạn nhập email vào ô Username.  
Thông báo lỗi đăng nhập được giữ chung cho trường hợp email không tồn tại và mật khẩu sai, tránh tiết lộ tài khoản nào đã đăng ký.

## 9. Bảo vệ API bằng JWT

Tạo file `app/auth_dependencies.py`:
```py
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.database import get_db
```

Trong project hiện tại, get_db nằm ở app/dependencies.py, không phải app.database.py.  
Vì vậy, dùng bản hoàn chỉnh dưới đây cho file này:

```py
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import User
from app.security import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        subject = payload.get("sub")

        if not isinstance(subject, str):
            raise credentials_error

        user_id = int(subject)
    except (InvalidTokenError, ValueError, TypeError):
        raise credentials_error

    user = db.get(User, user_id)

    if user is None:
        raise credentials_error

    return user
```
Dependency `get_current_user()` thực hiện các bước:
1. Lấy bearer token từ request.
2. Xác minh chữ ký và thời hạn token.
3. Đọc user ID trong sub.
4. Tìm người dùng trong database.
5. Trả về user nếu hợp lệ; nếu không, trả 401 Unauthorized.

JWT hợp lệ không có nghĩa tài khoản vẫn tồn tại, vì vậy chúng ta vẫn kiểm tra database.

## 10. Tạo endpoint chỉ dành cho người đã đăng nhập

Tạo file `app/routers/me.py`:
```py
from fastapi import APIRouter, Depends

from app.auth_dependencies import get_current_user
from app.models import User
from app.schemas import UserRead

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserRead)
def read_my_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user
```

Cuối cùng, cập nhật `app/main.py` để đăng ký hai router mới:
```py
def run_test_db() -> FastAPI:
    app = FastAPI(title="Python Backend Learning API")
    app.include_router(me_router)
    app.include_router(users_router)
    app.include_router(auth_router)

@app.get("/")
def health_check():
    return {"status": "ok"}
```

Endpoint mới là `GET /users/me`.  
Bạn chỉ có thể truy cập endpoint này khi cung cấp token hợp lệ.

Nếu router `users.py` của bạn có endpoint `GET /users/{user_id}`, hãy đặt route `/me` trước route động đó trong cùng một router, hoặc giữ `/me` ở router riêng như ví dụ trên để tránh `/me` bị hiểu thành `user_id="me"`.

`me_router` chứa route cố định **`/users/me`**, còn `users_router` chứa route động **`/users/{user_id}`**.  
Hai route cùng khớp phần đầu `/users/`, nhưng nếu route động được thử trước, FastAPI có thể xem `"me"` là giá trị của `user_id`. Sau đó Pydantic cố chuyển `"me"` thành `int` và trả 422. Việc đã authorize trên Swagger không ảnh hưởng đến bước chọn route này.

Đặt `me_router` trước `users_router` khiến route cố định được xét trước và xử lý `/users/me`.

**Quy tắc sắp xếp:** đặt route cụ thể trước route tổng quát hoặc có tham số động. Ví dụ:

```text
/users/me
/users/{user_id}
```

Thứ tự chỉ quan trọng khi các route có thể khớp cùng một URL; các router có đường dẫn không chồng lấn thì có thể include theo thứ tự nào cũng được.  
Quy tắc này cũng áp dụng khi khai báo route trong cùng một router.



## 11. Chạy thử toàn bộ luồng
Khởi động server:
```powershell
uvicorn app.main:run_test_db --factory --reload
```
Mở SWAGGER UI

1. Đăng ký: gọi POST /auth/register với body:
   json     {       "name": "An Nguyen",       "email": "an@example.com",       "password": "MyStrongPass123"     }
{
    "name": "An Nguyen",
    "email": "an@example.com",
    "password": "MyStrongPass123"
}   
2. Đăng nhập: gọi POST /auth/login. Nhập an@example.com vào username, mật khẩu vào password. Kết quả trả về access_token.
3. Xác thực: bấm nút Authorize trên Swagger, nhập thông tin theo hướng dẫn của giao diện. FastAPI sẽ sử dụng token cho endpoint được bảo vệ.
4. Kiểm tra: gọi GET /users/me. Khi token hợp lệ, API trả về thông tin user hiện tại.
Nếu gọi /users/me mà không có token, kết quả mong đợi là 401 Unauthorized.


- [x] Test 1
- [x] Test 2
```
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxNSIsImV4cCI6MTc5MjIyMzI1OX0.RYATfTiXr7w4ZgLtV_OUxNl2kVj8y6yxXTZs7snmpv8",
  "token_type": "bearer"
}
```
- [x] Test 3: Nhập id pw

![alt text](image.png)

- [x] Test 4
```json
{
  "id": 15,
  "name": "An Nguyen",
  "email": "an@example.com",
  "age": null
}
```

Một số lưu ý bảo mật

- Không lưu hoặc ghi log mật khẩu gốc.
- Không commit `JWT_SECRET_KEY` lên Git.
- Access token trong bài này hết hạn sau 30 phút; chưa có refresh token hoặc cơ chế thu hồi token.
- Kiểm tra quyền sở hữu tài nguyên ở mỗi endpoint cần phân quyền. Đăng nhập thành công không tự cấp quyền sửa/xóa dữ liệu của người khác.
- Nếu triển khai thực tế, hãy dùng HTTPS và có giới hạn số lần đăng nhập để giảm nguy cơ dò mật khẩu.