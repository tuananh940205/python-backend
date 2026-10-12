# Luồng chạy `uvicorn app.main:run_test_db --factory --reload`

Tài liệu này giải thích lệnh đang dùng trong project, từ lúc chạy Uvicorn đến
khi một request `GET /users/` truy vấn PostgreSQL. Nội dung mô tả code hiện có;
đây không phải hướng dẫn thay đổi kiến trúc ứng dụng.

## 1. Lệnh này làm gì?

```powershell
uvicorn app.main:run_test_db --factory --reload
```

Lệnh khởi chạy Uvicorn làm máy chủ ASGI cho ứng dụng FastAPI. Ứng dụng được
tạo bằng hàm `run_test_db` trong module `app.main`. Khi file Python được sửa,
Uvicorn khởi động lại tiến trình phục vụ ứng dụng để nạp thay đổi.

Mặc định của Uvicorn trong lệnh này là:

- Địa chỉ bind: `127.0.0.1` (chỉ máy hiện tại).
- Cổng: `8000`.
- Chế độ reload dành cho phát triển.

Có thể mở tài liệu API tại `http://127.0.0.1:8000/docs`. Endpoint danh sách user
trong ứng dụng này là `GET http://127.0.0.1:8000/users/`; không có endpoint
đường dẫn `/get`.

## 2. Phân tích từng phần của lệnh

| Phần | Ý nghĩa |
| --- | --- |
| `uvicorn` | Chạy chương trình máy chủ ASGI Uvicorn từ môi trường Python đang được kích hoạt, ví dụ `.venv`. |
| `app.main` | Import module Python `main` trong package `app`, tương ứng file `app/main.py`. |
| `:` | Phân cách module Python và đối tượng cần tìm trong module đó. |
| `run_test_db` | Tên hàm trong `app/main.py` trả về đối tượng ứng dụng FastAPI. |
| `--factory` | Báo cho Uvicorn rằng `app.main:run_test_db` là hàm factory `() -> ASGI app`; Uvicorn gọi hàm để lấy ứng dụng. |
| `--reload` | Bật tiến trình theo dõi thay đổi source và khởi động lại tiến trình server khi phát hiện thay đổi. Dùng cho phát triển, không nên dùng làm chế độ triển khai production. |

Nếu bỏ `--factory`, Uvicorn sẽ hiểu đối tượng sau dấu `:` là một ứng dụng ASGI
đã được tạo sẵn. Trong cách chạy hiện tại, `run_test_db` là một hàm, vì vậy
`--factory` cần thiết để gọi hàm đó.

Tương đương về ý tưởng:

```python
from app.main import run_test_db

app = run_test_db()
# Sau đó đưa app cho máy chủ ASGI phục vụ request.
```

Uvicorn thực hiện việc import, gọi factory và quản lý máy chủ; người dùng không
cần tự gọi đoạn mã trên khi chạy lệnh CLI.

## 3. Thứ tự khởi động

```text
PowerShell
  └─ uvicorn app.main:run_test_db --factory --reload
       ├─ tiến trình giám sát reload (reloader)
       └─ tiến trình server (worker)
            ├─ import app.main
            │    ├─ chạy các import ở đầu app/main.py
            │    ├─ import router users và các dependency của router
            │    └─ đọc cấu hình / khởi tạo các đối tượng engine ở cấp module
            ├─ gọi run_test_db() vì có --factory
            ├─ tạo FastAPI và đăng ký các route của ứng dụng
            └─ phục vụ request trên 127.0.0.1:8000
```

Khi `--reload` bật, Uvicorn có một tiến trình giám sát và một tiến trình server.
Trên Windows, tiến trình con được tạo bằng cơ chế multiprocessing `spawn`.
Vì vậy module ứng dụng được import trong tiến trình server; các lệnh import và
khởi tạo ở cấp module có thể được thực thi lại khi worker được khởi động lại.

Thứ tự chi tiết trong code:

1. Python tìm `uvicorn` trong môi trường đã kích hoạt.
2. Uvicorn đọc chuỗi `app.main:run_test_db`.
3. Uvicorn import `app.main`, tức thực thi các câu lệnh import ở đầu
   [app/main.py](./app/main.py).
4. Các module được import có thể tiếp tục import module khác. Ví dụ,
   `app.routers.users` import `app.dependencies`, model `User` và các Pydantic
   schema; dependency này import `SessionLocal` từ `app.database`. `app.main`
   cũng import `app.routers.chat`, `models.product`, `services.product_service`
   và `app.db.session.engine` ở cấp module. Chúng được import lúc khởi động,
   nhưng không được factory `run_test_db()` dùng để đăng ký route hoặc xử lý
   request.
5. `app.database` gọi `load_dotenv()`, đọc `DATABASE_URL`, tạo SQLAlchemy
   `engine` và cấu hình `SessionLocal`. Tạo engine chưa có nghĩa là đã mở kết
   nối mạng tới PostgreSQL; kết nối thường được mở khi session thực thi truy
   vấn đầu tiên.
6. `app.main` cũng import `engine` từ `app.db.session`. Module này đọc
   `settings.database_url` từ `app.core.config` và tạo một engine khác. Trong
   code hiện tại, `run_test_db` không dùng engine này; endpoint users lấy
   session từ `app.database.SessionLocal`.
7. Uvicorn gọi `run_test_db()` vì có `--factory`.
8. Hàm tạo `FastAPI(title="Python Backend Learning API")`, gắn router users,
   khai báo route health check `/`, rồi trả về app cho Uvicorn.
9. Uvicorn bắt đầu nhận request.

### Hàm `run_test_db()`

Trong [app/main.py](./app/main.py), factory có dạng:

```python
def run_test_db() -> FastAPI:
    app = FastAPI(title="Python Backend Learning API")
    app.include_router(users_router)

    @app.get("/")
    def health_check():
        return {"status": "ok"}

    return app
```

- `FastAPI(...)` tạo đối tượng ứng dụng.
- `app.include_router(users_router)` đăng ký các endpoint đã khai báo trong
  `app/routers/users.py`.
- `@app.get("/")` đăng ký health check đơn giản; route này chỉ trả trạng thái
  `"ok"` và không kiểm tra kết nối PostgreSQL.
- `return app` trả ứng dụng đã cấu hình cho Uvicorn.

Factory này chỉ gắn router users và route `/`. Dù module `app.main` cũng import
các router chat cho factory khác, `run_test_db()` không gọi
`app.include_router(chat.router)`, nên app khởi chạy bằng lệnh này không có
route `/chat`.

Các route được kiểm tra từ OpenAPI của factory hiện tại:

| Method | Đường dẫn | Mục đích |
| --- | --- | --- |
| `GET` | `/` | Health check tĩnh, trả `{"status": "ok"}`. |
| `GET` | `/users/` | Lấy danh sách user từ PostgreSQL. |
| `POST` | `/users/` | Tạo user. |
| `GET` | `/users/{user_id}` | Lấy một user theo ID. |
| `PATCH` | `/users/{user_id}` | Cập nhật một phần thông tin user. |
| `DELETE` | `/users/{user_id}` | Xóa user. |

## 4. Các file và vai trò trong luồng

### `app/main.py` — điểm vào của ứng dụng

- Uvicorn import module này theo tên `app.main`.
- Chứa hàm factory `run_test_db()`.
- Factory tạo FastAPI app, gắn router users và thêm health check `/`.
- File còn chứa các factory/bài học khác; Uvicorn chỉ gọi factory được nêu sau
  dấu `:` trong lệnh.
- Các import ở đầu module được thực thi khi import, kể cả một số import không
  được `run_test_db()` sử dụng. Điều này khác với việc các route tương ứng được
  đăng ký vào app.
- Cụ thể, `text`, `Product`, `engine` và `product_service` đang được import ở
  cấp module nhưng không được factory này gọi. `users` và `chat` cũng được
  import cho factory `create_app_router()`; riêng `run_test_db()` gắn router
  users bằng alias `users_router` và không gắn router chat.

### `app/routers/users.py` — định nghĩa HTTP endpoint

Router được khai báo với:

```python
router = APIRouter(prefix="/users", tags=["Users"])
```

Prefix `/users` được ghép với đường dẫn decorator. Chẳng hạn:

```python
@router.get("/")
def get_users(...):
    ...
```

được phục vụ tại `GET /users/`.

Endpoint danh sách:

1. Tạo câu truy vấn SQLAlchemy `select(User).order_by(User.id)`.
2. Gọi `db.scalars(statement).all()` để thực thi câu truy vấn và lấy các ORM
   object `User`.
3. Trả danh sách object về cho FastAPI.

Các endpoint khác trong cùng router dùng `db.get`, `db.add`, `db.commit`,
`db.refresh` hoặc `db.delete`, tùy thao tác.

### `app/dependencies.py` — cung cấp session cho request

Endpoint khai báo tham số:

```python
db: Session = Depends(get_db)
```

`Depends(get_db)` nói với FastAPI rằng trước khi gọi endpoint, hãy chạy
`get_db()` để cung cấp đối số `db`.

`get_db()` trong `app/dependencies.py`:

1. Tạo session mới bằng `SessionLocal()`.
2. `yield db` để FastAPI đưa session vào endpoint.
3. Sau khi request hoàn tất, chạy khối `finally` và gọi `db.close()`.

Đây là dependency dạng generator nhằm giới hạn vòng đời session theo request.

### `app/database.py` — cấu hình kết nối đang dùng bởi router users

- `load_dotenv()` nạp biến môi trường từ file `.env` nếu có.
- `DATABASE_URL = os.getenv("DATABASE_URL")` đọc URL kết nối.
- Nếu biến này không được cấu hình, module dừng sớm bằng `RuntimeError`.
- `create_engine(DATABASE_URL, echo=True)` tạo SQLAlchemy engine và bật log câu
  SQL.
- `sessionmaker(...)` tạo factory `SessionLocal`, dùng để mở session trong
  `get_db()`.

Không đưa giá trị thật của `DATABASE_URL` vào tài liệu hoặc commit. File `.env`
phải tồn tại ở môi trường local và cần trỏ tới PostgreSQL có thể truy cập.

### `app/models.py` — ánh xạ bảng `users`

Lớp SQLAlchemy `User` khai báo bảng `users` và các cột:

- `id`: khóa chính.
- `name`: chuỗi, không nullable.
- `email`: chuỗi, không nullable.
- `age`: số nguyên, nullable.

`select(User)` dùng lớp này để SQLAlchemy biết bảng/cột cần truy vấn và cách
chuyển các hàng kết quả thành object Python.

### `app/schemas/__init__.py` — định dạng/kiểm tra request và response

Export các schema `UserCreate`, `UserUpdate` và `UserRead`.

- `UserCreate` kiểm tra dữ liệu tạo user.
- `UserUpdate` kiểm tra dữ liệu cập nhật.
- `UserRead` mô tả dữ liệu user trả về và bật
  `ConfigDict(from_attributes=True)` để đọc thuộc tính từ ORM object.

Ở `GET /users/`, FastAPI dùng `response_model=list[UserRead]` để định dạng và
kiểm tra danh sách object trước khi chuyển thành JSON.

Ngoài các schema trên, `app.dependencies` import `ChatService` và
`UserService`; các service này lần lượt import schema chat và schema user trong
`app/schemas/chat.py` và `app/schemas/user.py`. Việc import các class này không
có nghĩa là `GET /users/` gọi service chat hoặc user. Endpoint đang truy vấn
ORM trực tiếp bằng `select(User)`.

### `app/core/config.py` và `app/db/session.py` — engine bổ sung được import

`app/core/config.py` dùng Pydantic Settings để đọc `DATABASE_URL` từ môi trường
hoặc `.env`. `app/db/session.py` dùng URL đó để tạo một engine khác với
`app.database.engine`.

`app/main.py` hiện import `engine` từ `app.db.session`, nhưng `run_test_db()` và
router users không dùng engine này để thực thi truy vấn. Luồng GET users sử dụng
`app.database.SessionLocal` qua `get_db()`. Việc import engine này vẫn là một
phần của lúc import `app.main`, nên cấu hình hợp lệ vẫn cần có trong môi
trường.

## 5. Luồng một request `GET /users/`

```text
Client / Swagger UI
  │  GET http://127.0.0.1:8000/users/
  ▼
Uvicorn nhận HTTP request
  ▼
FastAPI tìm route GET /users/ đã đăng ký từ users_router
  ▼
FastAPI phân giải Depends(get_db)
  ├─ SessionLocal() tạo SQLAlchemy Session
  └─ đưa session vào tham số db của get_users
  ▼
get_users(db)
  ├─ statement = select(User).order_by(User.id)
  └─ db.scalars(statement).all()
       ▼
     SQLAlchemy lấy kết nối từ engine / connection pool
       ▼
     PostgreSQL thực thi SELECT trên bảng users
       ▼
     Các hàng kết quả được chuyển thành ORM object User
  ▼
FastAPI xác thực/serialize theo list[UserRead]
  ▼
HTTP response JSON, ví dụ []
  ▼
Dependency chạy finally và db.close()
```

Nếu bảng có dữ liệu, response là một JSON array gồm các object user. Nếu bảng
chưa có hàng nào, response là `[]` với status `200`. Nếu database hoặc bảng
không tồn tại, lỗi thường xuất hiện khi truy vấn cần mở kết nối hoặc chạy SQL;
health check `/` vẫn có thể trả `200` vì handler hiện tại không chạm tới
database.

## 6. Cấu hình PostgreSQL và điều lệnh này không tự làm

`DATABASE_URL` phải xác định đúng host, port, database và thông tin xác thực
PostgreSQL. `.env` không nên commit nếu chứa mật khẩu.

Lệnh Uvicorn này **không**:

- tạo database PostgreSQL;
- tạo/sửa bảng từ model;
- chạy Alembic migration;
- seed dữ liệu user.

Database và schema cần được tạo/cập nhật riêng trước khi endpoint truy vấn.
Khai báo model Python tự nó không tạo bảng trong database.

## 7. Cách dừng và một số dấu hiệu log

- Nhấn `Ctrl+C` trong terminal để dừng tiến trình giám sát và server.
- `Uvicorn running on http://127.0.0.1:8000` cho biết địa chỉ/cổng server.
- `Started reloader process` là tiến trình theo dõi thay đổi khi dùng
  `--reload`.
- `Started server process` và `Application startup complete` cho biết worker
  đã khởi động ứng dụng.
- `GET /docs ... 200` chỉ xác nhận Swagger UI được phục vụ; chưa chứng minh
  PostgreSQL truy vấn thành công.
- `GET /users/ ... 200` mới là bằng chứng request endpoint trả thành công;
  `500` kèm lỗi `OperationalError` thường cần kiểm tra PostgreSQL, database,
  credentials hoặc kết nối.

## 8. Tự kiểm tra để củng cố hiểu biết

Sau khi đọc, thử giải thích bằng lời của bạn:

1. Vì sao lệnh có `--factory` và hàm `run_test_db()` cần trả về app?
2. Vì sao URL `/users/` được tạo từ cả `prefix="/users"` và decorator `"/"`?
3. Khi nào `get_db()` tạo session, và session được đóng ở đâu?
4. Vì sao gọi `/` có thể thành công trong khi gọi `/users/` gặp lỗi database?
5. File nào định nghĩa route, file nào cung cấp DB session, file nào mô tả bảng?
6. Khi sửa file Python, phần nào của lệnh `--reload` sẽ khởi động lại?
