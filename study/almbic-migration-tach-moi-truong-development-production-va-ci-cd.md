<p align="center" style="font-size: 30px">
    <b>
        Alembic Migration, tách môi trường Development/Production và CI/CD
    </b>
</p>

Trong bài trước, bạn đã đóng gói `FastAPI` và `PostgreSQL` bằng `Docker Compose`.  
Bây giờ chúng ta sẽ nâng cấp quy trình để mỗi lần thay đổi database hoặc code, bạn có thể kiểm tra và triển khai một cách có kiểm soát.

Bài này gồm ba phần:
1. `Alembic`: quản lý lịch sử thay đổi schema database.
2. `Docker Compose Development/Production`: tách môi trường lập trình và môi trường chạy thật.
3. `GitHub Actions`: tự động chạy test khi đẩy code lên GitHub.

Mục tiêu là xây dựng quy trình gần với cách một Backend Developer làm việc trong doanh nghiệp.

# 1. Alembic giải quyết vấn đề gì?

Giả sử database của bạn đang có bảng `users`:
```sql
CREATE TABLE users (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL
);
```
Sau này, bạn cần thêm `role` để triển khai RBAC.  
Nếu sửa database thủ công trên máy mình, đồng đội hoặc server có thể không biết phải thực hiện thay đổi nào.

Alembic cho phép bạn lưu thay đổi schema thành các migration có phiên bản.
```
        Revision A
      Tạo bảng users
             ↓
         Revision B
   Thêm cột password_hash
             ↓
         Revision C
   Thêm role và constraint

Alembic theo dõi revision hiện tại của database và áp dụng các migration còn thiếu.
```

Liên hệ với Unity: migration giống một chuỗi thay đổi có phiên bản đối với schema dữ liệu, nhưng không giống hoàn toàn với Git commit.  
Git lưu lịch sử source code; Alembic lưu các bước thay đổi cấu trúc database.

# 2. Bước 1 — Khởi tạo Alembic

Tại thư mục gốc D:\projects\python\python-backend, kích hoạt môi trường ảo và cài Alembic nếu chưa có:
```
cd D:\projects\python\python-backend
.venv\Scripts\Activate.ps1
python -m pip install alembic
```
Khởi tạo thư mục migration:
```powershell
python -m alembic init migrations
```
Cấu trúc mới:
```
python-backend/
├── app/
├── migrations/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
├── Dockerfile
├── compose.yaml
└── requirements.txt
```

Nếu `migrations/` và `alembic.ini` đã tồn tại, không chạy lại lệnh khởi tạo; hãy chỉnh sửa các file hiện có.

# 3. Bước 2 — Kết nối Alembic với SQLAlchemy models
Mở `migrations/env.py`.

Tìm phần import `target_metadata` và điều chỉnh để Alembic nhận diện metadata của các model trong project:
```py
from app.database import Base
from app import models

target_metadata = Base.metadata
```
`models` cần được import để các model như `User` và `AuthSession` được đăng ký với `Base.metadata`.

Tiếp theo, trong `migrations/env.py`, trước khi Alembic sử dụng URL database, hãy nạp biến môi trường:
```py
import os
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if database_url:
    config.set_main_option(
        "sqlalchemy.url",
        database_url.replace("%", "%%"),
    )
```

Đoạn này dùng `config` đã được tạo sẵn trong file `env.py`.  
Đặt nó sau phần khởi tạo `config`, trước khi chạy migration.  
Giữ lại các hàm `run_migrations_offline()` và `run_migrations_online()` mà Alembic tạo mặc định.

Nếu bạn dùng `.env.docker` thay vì `.env`, khi chạy Alembic từ máy Windows, hãy nạp đúng file đó hoặc thiết lập `DATABASE_URL` trong PowerShell.  
Trong container, Compose sẽ truyền các biến từ `env_file`.

## Vì sao phải cấu hình `target_metadata`?

Khi chạy:
```powershell
python -m alembic revision --autogenerate -m "add auth sessions"
```
Result
```bash
(.venv) PS D:\projects\python\python-backend> python -m alembic revision --autogenerate -m "add auth sessions"
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.schemas
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.tables
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.types
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.constraints
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.defaults
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.comments
INFO  [alembic.autogenerate.compare.constraints] Detected removed index 'idx_posts_user_id' on 'posts'
INFO  [alembic.autogenerate.compare.constraints] Detected removed index 'idx_posts_user_id_id' on 'posts'
INFO  [alembic.autogenerate.compare.tables] Detected removed table 'posts'
INFO  [alembic.autogenerate.compare.tables] Detected removed table 'store_products'
INFO  [alembic.autogenerate.compare.constraints] Detected removed index 'idx_users_email' on 'users'
INFO  [alembic.autogenerate.compare.constraints] Detected removed unique constraint 'uq_user_email' on 'users'
INFO  [alembic.autogenerate.compare.constraints] Detected removed unique constraint 'uq_users_email' on 'users'
INFO  [alembic.autogenerate.compare.constraints] Detected added unique constraint None on '('name',)'
D:\projects\python\python-backend\.venv\Lib\site-packages\alembic\autogenerate\render.py:484: UserWarning: Autogenerate rendered a drop_constraint() directive for an unnamed constraint on table 'users'; the migration will fail unless a constraint name is added to the directive.  Consider using a naming convention so that constraint names are known ahead of time.
  util.warn(
Generating D:\projects\python\python-backend\migrations\versions\435c71cd15ed_add_auth_sessions.py ...  done
```

Alembic sẽ so sánh schema database với metadata của SQLAlchemy models và đề xuất migration.

Tuy nhiên, `--autogenerate không bảo đảm tạo migration hoàn chỉnh`. Bạn phải đọc file được sinh ra để kiểm tra cột, constraint, index, kiểu dữ liệu và các thao tác có nguy cơ mất dữ liệu.

# 4. Bước 3 — Tạo migration đầu tiên cho database Docker

Đây là điểm cần chú ý với project của bạn: database PostgreSQL cài trên Windows có thể đã chứa `users`, `posts` và các cột được thêm trong các bài học trước.  
Không nên tạo một migration khởi tạo rồi áp dụng nó lên database đã có các bảng đó, vì có thể gặp lỗi bảng đã tồn tại.

Với database Docker mới, bạn có thể tạo migration nền từ toàn bộ model hiện tại.

Trước hết, bảo đảm các model đã đầy đủ, bao gồm `User`, `Post` nếu có, và `AuthSession`. Sau đó tạo revision:

```powershell
python -m alembic revision --autogenerate -m "initial schema"
```
Result
```bash
(.venv) PS D:\projects\python\python-backend> python -m alembic revision --autogenerate -m "initial schema"
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
ERROR [alembic.util.messaging] Target database is not up to date.
FAILED: Target database is not up to date.
```
Mở file vừa tạo trong `migrations/versions/` và kiểm tra nó có các thao tác tạo bảng mong muốn hay không.

Nếu migration sinh ra thiếu bảng, không làm gì, hoặc có các thao tác không mong muốn, hãy dừng lại và sửa trước khi chạy upgrade.

Áp dụng migration vào database Docker:
```powershell
docker compose --env-file .env.docker run --rm api alembic upgrade head
```
Result
```bash
(.venv) PS D:\projects\python\python-backend> docker compose --env-file .env.docker run --rm api alembic upgrade head
[+] run 1/1
 ✔ Container python-backend-db-1 Running                                                                                                                                                                 0.0s
Container python-backend-db-1 Waiting
Container python-backend-db-1 Healthy
Container python-backend-api-run-1d302f1712a6 Creating
Container python-backend-api-run-1d302f1712a6 Created
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

Lệnh này yêu cầu `Docker Compose` chạy một container API tạm thời, thực thi migration rồi kết thúc.  
Nó không có nghĩa là API service đang chạy sẽ tự động restart.

Kiểm tra revision hiện tại:
```powershell
docker compose --env-file .env.docker run --rm api alembic current
```
Result
```bash
(.venv) PS D:\projects\python\python-backend> docker compose --env-file .env.docker run --rm api alembic current
[+] run 1/1
 ✔ Container python-backend-db-1 Running                                                                                                                                                                 0.0s
Container python-backend-db-1 Waiting
Container python-backend-db-1 Healthy
Container python-backend-api-run-9dfb22250fa3 Creating
Container python-backend-api-run-9dfb22250fa3 Created
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
435c71cd15ed (head)
```
Và kiểm tra lịch sử:
```powershell
docker compose --env-file .env.docker run --rm api alembic history
```
Result
```bash
(.venv) PS D:\projects\python\python-backend> docker compose --env-file .env.docker run --rm api alembic history
[+] run 1/1
 ✔ Container python-backend-db-1 Running                                                                                                                                                                 0.0s
Container python-backend-db-1 Waiting
Container python-backend-db-1 Healthy
Container python-backend-api-run-363bcde281df Creating
Container python-backend-api-run-363bcde281df Created
<base> -> 435c71cd15ed (head), add auth sessions
```
Không chạy `alembic stamp head` chỉ để né lỗi migration. `stamp` đánh dấu revision mà không thực thi các thao tác thay đổi schema.  
Chỉ dùng khi bạn đã xác minh database thực tế khớp với revision đó.

# 5. Bước 4 — Tách cấu hình Development và Production
Trong quá trình phát triển, bạn thường muốn sửa code trên Windows và thấy thay đổi ngay.  
Nhưng môi trường production không nên dùng `--reload` hoặc `bind-mount` toàn bộ source code từ máy lập trình.

Ta sẽ dùng hai file Compose.

## 5.1. Cập nhật `compose.yaml`
Đây là cấu hình cơ sở, không mở cổng PostgreSQL trực tiếp ra máy host:
```yaml
services:
  db:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test:
        [
          "CMD-SHELL",
          "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"
        ]
      interval: 5s
      timeout: 5s
      retries: 10

  api:
    build: .
    restart: unless-stopped
    env_file:
      - .env.docker
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
```
Git diff
![alt text](image-2.png)
## 5.2. Tạo `compose.dev.yaml`
```yaml
services:
  db:
    ports:
      - "5433:5432"

  api:
    volumes:
      - ./:/app
    command:
      [
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--reload"
      ]
```
Trong development, API sẽ đọc code từ thư mục project được mount vào /app.  
Khi bạn sửa file Python, Uvicorn có thể tự reload.

Chạy môi trường development:
```powershell
docker compose `
  --env-file .env.docker `
  -f compose.yaml `
  -f compose.dev.yaml `
  up --build -d
```
Result
```bash
(.venv) PS D:\projects\python\python-backend> docker compose `
>>   --env-file .env.docker `
>>   -f compose.yaml `
>>   -f compose.dev.yaml `
>>   up --build -d
[+] Building 14.2s (16/16) FINISHED
 => [internal] load local bake definitions                                                                                                                                                              0.0s
 => => reading from stdin 527B                                                                                                                                                                          0.0s
 => [internal] load build definition from Dockerfile                                                                                                                                                    0.0s
 => => transferring dockerfile: 419B                                                                                                                                                                    0.0s
 => [internal] load metadata for docker.io/library/python:3.12-slim                                                                                                                                     1.2s
 => [internal] load .dockerignore                                                                                                                                                                       0.0s
 => => transferring context: 166B                                                                                                                                                                       0.0s
 => [1/9] FROM docker.io/library/python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1                                                                               0.0s
 => => resolve docker.io/library/python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1                                                                               0.0s
 => [internal] load build context                                                                                                                                                                       0.0s
 => => transferring context: 9.59kB                                                                                                                                                                     0.0s
 => CACHED [2/9] WORKDIR /app                                                                                                                                                                           0.0s
 => [3/9] COPY requirements.txt .                                                                                                                                                                       0.0s
 => [4/9] RUN pip install --no-cache-dir -r requirements.txt                                                                                                                                           10.3s
 => [5/9] COPY app ./app                                                                                                                                                                                0.0s
 => [6/9] COPY models ./models                                                                                                                                                                          0.0s
 => [7/9] COPY services ./services                                                                                                                                                                      0.0s
 => [8/9] COPY migrations ./migrations                                                                                                                                                                  0.0s
 => [9/9] COPY alembic.ini* ./                                                                                                                                                                          0.0s
 => exporting to image                                                                                                                                                                                  2.2s
 => => exporting layers                                                                                                                                                                                 1.7s
 => => exporting manifest sha256:3c558a763bfd15f2ece0455864a7025fb82074907772a377a0a6d8a81bfa10e9                                                                                                       0.0s
 => => exporting config sha256:94a6b9b7d4b7abc16d7f27cfde29f41a713c9c350c868016d90349b6eefb1797                                                                                                         0.0s
 => => exporting attestation manifest sha256:ccfa6133210da5dafcce73ebd4f5c0d40be21e48ae66226a3cbbd87c8c0f6ee2                                                                                           0.0s
 => => exporting manifest list sha256:87ac680ca0b83ed2f4a9b44b913a606fe09c6d5268736553d7fed83f36864ecd                                                                                                  0.0s
 => => naming to docker.io/library/python-backend-api:latest                                                                                                                                            0.0s
 => => unpacking to docker.io/library/python-backend-api:latest                                                                                                                                         0.4s
 => resolving provenance for metadata file                                                                                                                                                              0.0s
[+] up 3/3
 ✔ Image python-backend-api       Built                                                                                                                                                                 14.4s
 ✔ Container python-backend-db-1  Healthy                                                                                                                                                                0.6s
 ✔ Container python-backend-api-1 Started
```
Để dừng:
```powershell
docker compose `
  --env-file .env.docker `
  -f compose.yaml `
  -f compose.dev.yaml `
  down
```
Result
```bash
(.venv) PS D:\projects\python\python-backend> docker compose `
>>   --env-file .env.docker `
>>   -f compose.yaml `
>>   -f compose.dev.yaml `
>>   down
[+] down 3/3
 ✔ Container python-backend-api-1 Removed                                                                                                                                                                3.3s
 ✔ Container python-backend-db-1  Removed                                                                                                                                                                0.3s
 ✔ Network python-backend_default Removed
```
Với cách tổ chức này:
- `compose.yaml`: cấu hình cơ sở cho việc chạy ứng dụng.
- `compose.dev.yaml`: chỉ chứa những thay đổi dành cho phát triển.
- Production không cần bật --reload hay mount source code từ máy host.

Lưu ý: đây mới là cấu hình cơ sở theo hướng production, chưa phải một hệ thống production hoàn chỉnh.  
Khi deploy thật, bạn cần quản lý secret riêng, HTTPS, backup, giám sát, migration có kiểm soát và chiến lược triển khai phù hợp.

# 6. Bước 5 — Tự động chạy test bằng GitHub Actions

Bây giờ, mỗi khi bạn push code lên GitHub hoặc tạo Pull Request, chúng ta muốn tự động kiểm tra code trước khi merge.

Tạo file:
```
.github/
└── workflows/
    └── ci.yaml
```
Nội dung `ci.yaml`:
```yaml
name: Backend CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: backend_user
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: backend_learning
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U backend_user -d backend_learning"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10

    env:
      DATABASE_URL: postgresql+psycopg://backend_user:test_password@localhost:5432/backend_learning
      JWT_SECRET_KEY: ci-only-test-secret-not-for-production
      JWT_ALGORITHM: HS256
      ACCESS_TOKEN_EXPIRE_MINUTES: 30

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest httpx

      - name: Apply migrations
        run: python -m alembic upgrade head

      - name: Run tests
        run: python -m pytest -v
```
Trước khi dùng workflow này, hãy xác nhận:

1. Các migration có thể tạo schema trên một PostgreSQL database hoàn toàn mới.
2. `requirements.txt` có đầy đủ dependency cần thiết.
3. Các biến môi trường phù hợp với cách app/database.py và app/security.py khởi tạo ứng dụng.
4. Bộ test có thể chạy với PostgreSQL của CI; nếu một số test chỉ dành cho unit test, hãy bảo đảm chúng không phụ thuộc vào dữ liệu hoặc dịch vụ không được thiết lập.

Các phiên bản GitHub Actions trong ví dụ là phiên bản minh họa; khi dùng lâu dài, nên kiểm tra phiên bản được khuyến nghị và cập nhật theo chính sách bảo mật của repository.

CI khác CD như thế nào?
```
CI — Continuous Integration
Tự động cài dependency, chạy migration và test để phát hiện lỗi sớm.

CD — Continuous Delivery/Deployment
Tiếp tục build image, đưa ứng dụng tới môi trường staging hoặc production sau khi các điều kiện kiểm tra đạt yêu cầu.
```
