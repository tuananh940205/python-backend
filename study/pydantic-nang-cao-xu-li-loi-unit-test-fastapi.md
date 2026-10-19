<p align="center" style="font-size: 30px">
    <b>Pydantic nâng cao, xử lý lỗi và Unit Test trong FastAPI</b>
</p>

## 1. Pydantic: Validation dữ liệu đầu vào
Cài đặt thư viện kiểm tra email
```bash
pip install email-validator
```

Cập nhật `app/schemas.py`

```python
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    age: int | None = Field(default=None, ge=0, le=150)

class UserUpdate(BaseModel):
    name: str | None = Field(
        default=None, min_length=1, max_length=100
    )
    email: EmailStr | None = None
    age: int | None = Field(default=None, ge=0, le=150)

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    age: int | None
```

Thiết lập các ràng buộc về giá trị dữ liệu đầu vào

Các quy tắc mới:
Khai báo | Ý nghĩa
|-|-|
EmailStr | Kiểm tra email theo định dạng được hỗ trợ
ge=0 | Giá trị lớn hơn hoặc bằng 0
le=150 | Giá trị nhỏ hơn hoặc bằng 150
max_length=100 | Giới hạn độ dài chuỗi
int \| None | Giá trị có thể là số nguyên hoặc None

Đoạn logic cập nhật value vào database
```python
def update_user(db: Session, user_id: int, payload: UserUpdate) -> User:
    user = get_user(db, user_id)
    changes = payload.model_dump(exclude_unset=True)
```

Cập nhật `age = 35`
```
{
  "age": 35
}
```
Cập nhật `age = null`
```
{
  "age": null
}
```

## 2. Validation nghiệp vụ bằng `field_validator`

Pydantic có thể kiểm tra những quy tắc không chỉ là kiểu dữ liệu.  
Ví dụ, bạn muốn tự động loại bỏ khoảng trắng ở đầu và cuối tên.

Thêm vào `app/schemas.py`

```python
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    age: int | None = Field(default=None, ge=0, le=150)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Name cannot be blank")

        return value

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

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    age: int | None
```

Phân tích decorator
```py
@field_validator("name")
@classmethod
def normalize_name(cls, value: str | None) -> str | None:
    if value is None:
        return value

    value = value.strip()

    if not value:
        raise ValueError("Name cannot be blank")

    return value
```
- field_validator: validator decorator chuẩn hóa giá trị của `name`
- classmethod: biến hàm thành class method, nhận `cls` làm param đầu tiên

Ví dụ, input:

```
{
  "name": "  An Nguyen  ",
  "email": "an@example.com",
  "age": 30
}
```
sẽ được chuẩn hóa thành tên "An Nguyen" trước khi đến Service.

## 3. Xử lý lỗi database có hệ thống

Giả sử database từ chối một thao tác ghi dữ liệu. SQLAlchemy có thể ném ra lỗi như IntegrityError nếu vi phạm ràng buộc `UNIQUE`, `FOREIGN KEY` hoặc `CHECK`.

Không nên trả nguyên traceback hoặc thông báo SQL cho client, vì chúng có thể để lộ cấu trúc database và thông tin nội bộ.

### 3.1. Rollback khi ghi dữ liệu thất bại

Trong `app/services/user_service.py`, có thể cập nhật hàm `create_user` như sau:

```py
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.repositories import user_repository
from app.schemas import UserCreate


class DuplicateUserDataError(Exception):
    pass

def create_user(db: Session, payload: UserCreate) -> User:
    user = User(**payload.model_dump())

    try:
        user_repository.add(db, user)
        db.commit()
        db.refresh(user)
        return user

    except IntegrityError as error:
        db.rollback()
        raise DuplicateUserDataError(
            "User data violates a database constraint"
        ) from error

    except Exception:
        db.rollback()
        raise
```
Ở đây, `IntegrityError` được chuyển thành một lỗi ở cấp ứng dụng.  
Tên `DuplicateUserDataError` chỉ mang tính minh họa: `IntegrityError` cũng có thể do các ràng buộc khác, không chỉ dữ liệu trùng.  
Để phân loại chính xác, bạn cần kiểm tra constraint nào bị vi phạm.  
Và nhớ rằng bảng users hiện tại chưa có `UNIQUE` cho email, trừ khi bạn đã thêm constraint đó ở bài trước.  
Chưa có constraint thì không thể trông chờ database tự ngăn email trùng.

### 3.2. Chuyển lỗi ứng dụng thành HTTP response

Trong `app/routers/users.py`, import lỗi mới:
```py
from app.services.user_service import (
    DuplicateUserDataError,
    UserNotFoundError,
)
```
Sau đó sửa endpoint tạo user:
```py
@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        return user_service.create_user(db, payload)
    except DuplicateUserDataError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
```
`409 Conflict` cho biết yêu cầu xung đột với trạng thái hoặc ràng buộc dữ liệu hiện tại.

Một số mã HTTP nên nhớ:
Mã | Khi nào dùng
|-|-|
400 | Request không hợp lệ theo quy tắc của endpoint
404 |	Không tìm thấy tài nguyên
409 |	Xung đột với trạng thái hoặc ràng buộc dữ liệu
422 |	Dữ liệu request không vượt qua validation của FastAPI/Pydantic
500 |	Lỗi server không được xử lý cụ thể

Không nên bắt mọi lỗi rồi trả 400, bởi điều đó khiến client không phân biệt được lỗi input với lỗi hệ thống.

## 4. Viết Unit Test bằng pytest
Unit Test giúp kiểm tra từng phần nhỏ của chương trình. 

Ta có thể kiểm tra Service mà không cần mở kết nối PostgreSQL thật bằng cách thay các thao tác database bằng đối tượng giả.

### 4.1. Cài pytest

```bash
pip install pytest
```

Tạo thư mục:
```
tests/
└── test_user_service.py
```

### 4.2. Kiểm tra Service bằng fake session

Trong `tests/test_user_service.py`:

```py
import pytest

from app.schemas import UserCreate
from app.services import user_service

class FakeSession:
    def __init__(self, fail_commit=False):
        self.added = None
        # Ban đầu committed và rolled_back đều là False;
        # fail_commit=False khiến commit() không phát sinh lỗi.
        self.committed = False
        self.rolled_back = False
        self.fail_commit = fail_commit

    def add(self, obj):
        self.added = obj

    def commit(self):
        if self.fail_commit:
            raise RuntimeError("Simulated database failure")
        self.committed = True

    def refresh(self, obj):
        obj.id = 123

    def rollback(self):
        self.rolled_back = True

def test_create_user_success(monkeypatch):
    # Tạo một session giả
    db = FakeSession()
    # Tạo và kiểm tra dữ liệu đầu vào
    payload = UserCreate(
        name="  An Nguyen  ",
        email="an@example.com",
        age=30,
    )

    def fake_add(session, user):
        session.add(user)

    # thay tạm `user_repositiry.add` bằng `fake_add`.
    # Hàm giả này gọi session.add(user), nên đối tượng được ghi vào db.added thay vì được gửi tới database.
    monkeypatch.setattr(
        user_service.user_repository,
        "add",
        fake_add,
    )

    # User(**payload.model_dump()) tạo model User từ dữ liệu của payload.
    # user_repository.add(db, user) gọi hàm giả đã thay ở bước trước.
    # db.commit() chạy thành công và đặt db.committed = True.
    # db.refresh(user) của session giả đặt user.id = 123.
    # Service trả lại user.
    user = user_service.create_user(db, payload)

    # Các assert xác nhận ID, tên, email và trạng thái commit đúng; đồng thời xác nhận không rollback.
    # Vì tất cả đều đúng, test được đánh dấu PASSED.
    assert user.id == 123
    assert user.name == "An Nguyen"
    assert user.email == "an@example.com"
    assert db.committed is True
    assert db.rolled_back is False

def test_create_user_rolls_back_on_failure(monkeypatch):
    # tạo session giả có chủ đích ném RuntimeError khi gọi commit().
    db = FakeSession(fail_commit=True)
    payload = UserCreate(
        name="An Nguyen",
        email="an@example.com",
        age=30,
    )

    # Test tạo payload hợp lệ và thay user_repository.add bằng một lambda gọi session.add(user), tương tự test đầu.
    # Service tạo User, gọi hàm add giả, rồi tới db.commit(). Lần này commit() ném RuntimeError("Simulated database failure").
    monkeypatch.setattr(
        user_service.user_repository,
        "add",
        lambda session, user: session.add(user),
    )

    # Trong create_user, lỗi không phải IntegrityError, nên không vào nhánh đó; nó rơi vào except Exception. 
    # Service gọi db.rollback() rồi raise để ném tiếp chính lỗi ban đầu.
    with pytest.raises(RuntimeError):
        user_service.create_user(db, payload)

    assert db.rolled_back is True
```
Giải thích:
- `FakeSession` mô phỏng những phương thức mà `Service` sử dụng.
- `monkeypatch` thay `user_repository.add` bằng thao tác giả để test không truy vấn database.
- `pytest.raises(...)` xác nhận rằng lỗi dự kiến được ném ra.
- Hai test kiểm tra cả trường hợp thành công và trường hợp phải rollback.

Lưu ý về schema:
- test import UserCreate từ app/schemas/__init__.py, còn service import lớp UserCreate khác từ app/schemas/user.py để khai báo kiểu tham số.
- Python không tự kiểm tra kiểu annotation lúc chạy, nên test vẫn gọi được service; tuy nhiên, hai lớp cùng tên này có định nghĩa trường khác nhau.

Đây là unit test dùng mock/fake, không chứng minh PostgreSQL thực tế hoạt động đúng.  
Bạn vẫn nên có integration test với database kiểm thử riêng khi dự án lớn hơn.

### 4.3. Chạy test
Từ thư mục gốc python-backend:
```shell
python -m pytest -v
```
Kết quả
```
(.venv) PS D:\projects\python\python-backend> python -m pytest -v
================================================= test session starts =================================================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.7.0 -- D:\projects\python\python-backend\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\projects\python\python-backend
configfile: pyproject.toml
plugins: anyio-4.15.1
collected 2 items

tests/test_user_service.py::test_create_user_success PASSED                                                      [ 50%]
tests/test_user_service.py::test_create_user_rolls_back_on_failure PASSED                                        [100%]

================================================== warnings summary ===================================================
.venv\Lib\site-packages\_pytest\cacheprovider.py:469
  D:\projects\python\python-backend\.venv\Lib\site-packages\_pytest\cacheprovider.py:469: PytestCacheWarning: could not create cache path D:\projects\python\python-backend\.pytest_cache\v\cache\nodeids: [WinError 5] Access is denied: 'D:\\projects\\python\\python-backend\\pytest-cache-files-x1m4o2yi' -> 'D:\\projects\\python\\python-backend\\.pytest_cache'
    config.cache.set("cache/nodeids", sorted(self.cached_nodeids))

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
============================================ 2 passed, 1 warning in 0.48s =============================================
```

Kết quả mong đợi
```
tests/test_user_service.py::test_create_user_success PASSED
tests/test_user_service.py::test_create_user_rolls_back_on_failure PASSED

2 passed
```
#### Test

`python -m pytest -v` dùng Python đang được chọn để tải module `pytest`  
`-v` bật chế độ hiển thị chi tiết tên từng test.  
`Pytest` tìm test trong dự án, thu thập được hai hàm trong `tests/test_user_service.py`: `test_create_user_success` và `test_create_user_rolls_back_on_failure`.  
Sau bước thu thập, `pytest` chạy lần lượt phần thân của từng hàm

Nếu import app thất bại, hãy kiểm tra bạn có chạy lệnh từ thư mục gốc project và đã kích hoạt `.venv` chưa.

## 5. Kiểm thử validation của Pydantic

Tạo thêm file tests/test_user_schemas.py:
```py
import pytest
from pydantic import ValidationError

from app.schemas import UserCreate

def test_user_name_is_trimmed():
    user = UserCreate(
        name="  An Nguyen  ",
        email="an@example.com",
        age=30,
    )

    assert user.name == "An Nguyen"

def test_negative_age_is_rejected():
    with pytest.raises(ValidationError):
        UserCreate(
            name="An Nguyen",
            email="an@example.com",
            age=-1,
        )

def test_invalid_email_is_rejected():
    with pytest.raises(ValidationError):
        UserCreate(
            name="An Nguyen",
            email="not-an-email",
            age=30,
        )

def test_blank_name_is_rejected():
    with pytest.raises(ValidationError):
        UserCreate(
            name="   ",
            email="an@example.com",
            age=30,
        )
```

Nếu tất cả test đều qua, bạn đã tự động kiểm tra được cả Service và quy tắc đầu vào.

## 6. Phân biệt ba loại test

Loại test | Mục tiêu | Có cần PostgreSQL thật?
|-|-|-|
Unit Test | Kiểm tra một hàm hoặc lớp riêng lẻ | Không nhất thiết
Integration Test | Kiểm tra nhiều thành phần hoạt động cùng nhau | Thường có
API Test | Gửi HTTP request và kiểm tra response | Có thể dùng test database hoặc mock

Ví dụ với API tạo user:
- Unit Test: kiểm tra Service có rollback khi ghi dữ liệu lỗi.
- Integration Test: kiểm tra SQLAlchemy ghi user vào PostgreSQL thật.
- API Test: gửi POST /users/, xác nhận status 201 và response JSON.

Đừng nhầm việc một unit test chạy thành công với việc toàn bộ hệ thống đã hoạt động đúng.  
Mỗi loại test phát hiện một nhóm lỗi khác nhau.

## 8. Tổng kết
Trong bài này, bạn đã học:
- Pydantic nâng cao với EmailStr, Field và field_validator.
- Cách phân biệt validation dữ liệu với validation nghiệp vụ.
- Cách rollback transaction và chuyển lỗi database thành lỗi ứng dụng.
- Cách viết Unit Test bằng pytest, fake session và monkeypatch.