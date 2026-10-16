# 🚀 Quick Start - PostgreSQL + pgAdmin + Repository Pattern

## ⚡ 5 Phút Setup (First Time)

### 1️⃣ Start Docker Containers

```bash
# Ở thư mục project root
docker-compose up -d

# Kiểm tra containers đang chạy
docker-compose ps
```

✅ PostgreSQL sẽ chạy ở `localhost:5432`
✅ pgAdmin sẽ chạy ở `http://localhost:5050`

### 2️⃣ Cập Nhật .env

```env
DATABASE_URL=postgresql://postgres:your_secure_password_here@localhost:5432/python_backend
```

### 3️⃣ Test Connection

```bash
# Chạy FastAPI
uvicorn app.main:run_test_db --factory --reload

# Ở browser hoặc terminal khác:
curl http://localhost:8000/health/db

# Nếu output:
# {"database":"connected","result":1}
# → ✅ OK!
```

---

## 📊 Truy Cập pgAdmin 4

1. Mở browser → `http://localhost:5050`
2. **Email**: `admin@example.com`
3. **Password**: `admin_password`
4. Click **Servers** → **Register** → **Server**
5. Nhập:
   - **Name**: python_backend
   - **Host**: postgres
   - **Port**: 5432
   - **User**: postgres
   - **Password**: your_secure_password_here
6. **Save** → Done! 🎉

---

## 💻 Cách Tạo Query

### Pattern 1: Simple Query (Base Repository)

```python
# app/repositories/user_repository.py
from app.repositories.base import BaseRepository
from models.user import User

class UserRepository(BaseRepository[User]):
    def get_by_email(self, email: str):
        return self.db.query(User).filter(User.email == email).first()

# Sử dụng:
from app.repositories.user_repository import UserRepository

repo = UserRepository(db)
user = repo.get_by_email("john@example.com")
```

**SQL được generate:**
```sql
SELECT * FROM users WHERE email = :email LIMIT 1;
```

### Pattern 2: Complex Query

```python
# Repository method
def search_and_count(self, keyword: str):
    results = self.db.query(User).filter(
        User.name.ilike(f"%{keyword}%")
    ).all()
    return len(results), results

# SQL:
SELECT * FROM users WHERE name ILIKE :keyword;
```

### Pattern 3: Raw SQL (Khi cần)

```python
from app.services.database import DatabaseService

query = """
    SELECT u.id, u.name, COUNT(p.id) as post_count
    FROM users u
    LEFT JOIN posts p ON u.id = p.user_id
    WHERE u.is_active = true
    GROUP BY u.id
    ORDER BY post_count DESC
"""

results = DatabaseService.execute_raw_query(db, query)
```

---

## 📝 Workflow: Từ Model → Query → API

### Step 1: Define Model

```python
# models/user.py
from app.db.session import Base
from sqlalchemy import Column, Integer, String, Boolean

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
```

### Step 2: Create Migration

```bash
# Nếu dùng Alembic
alembic revision --autogenerate -m "Add User model"
alembic upgrade head

# Kiểm tra trong pgAdmin:
# Servers → python_backend → Databases → python_backend → Schemas → public → Tables
# → Bảng "users" xuất hiện
```

### Step 3: Create Repository

```python
# app/repositories/user_repository.py
from app.repositories.base import BaseRepository
from models.user import User

class UserRepository(BaseRepository[User]):
    def get_by_email(self, email: str):
        return self.db.query(User).filter(User.email == email).first()
    
    def search_by_name(self, name: str):
        return self.db.query(User).filter(
            User.name.ilike(f"%{name}%")
        ).all()
```

### Step 4: Create API Router

```python
# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.repositories.user_repository import UserRepository
from pydantic import BaseModel

router = APIRouter(prefix="/users", tags=["users"])

class UserCreate(BaseModel):
    name: str
    email: str
    username: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    if repo.get_by_email(user.email):
        raise HTTPException(status_code=400, detail="Email exists")
    return repo.create(user.dict())

@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user = repo.read_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404)
    return user

@router.get("/search/{name}")
def search_users(name: str, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    return repo.search_by_name(name)
```

### Step 5: Include Router in Main App

```python
# app/main.py
from fastapi import FastAPI
from app.routers.users import router

def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app
```

### Step 6: Test API

```bash
# Start server
uvicorn app.main:create_app --factory --reload

# Create user
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","email":"john@example.com","username":"johndoe"}'

# Get user
curl "http://localhost:8000/users/1"

# Search
curl "http://localhost:8000/users/search/John"
```

---

## 🔍 Inspect Data in pgAdmin

Sau khi tạo users, mở pgAdmin:

1. **Servers** → **python_backend** → **Databases** → **python_backend** → **Schemas** → **public** → **Tables** → **users**
2. **Right-click** → **View/Edit Data** → **All Rows**
3. Xem data vừa tạo

Hoặc **Query Tool** (F6):
```sql
SELECT * FROM users WHERE email = 'john@example.com';
```

---

## 📚 Các Methods Sẵn Có (Base Repository)

```python
repo = UserRepository(db)

# CREATE
user = repo.create({"name": "John", "email": "john@example.com", ...})

# READ
user = repo.read_by_id(1)
users = repo.read_all(skip=0, limit=10)

# UPDATE
user = repo.update(1, {"name": "Jane"})

# DELETE
repo.delete(1)
```

---

## 🆚 Khi Nào Dùng Cái Gì?

| Việc | Dùng Cái Gì |
|-----|-----------|
| Viết query trong Python code | **Repository Pattern** |
| Xem & sửa dữ liệu | **pgAdmin** |
| Query nhanh chóng khi dev | **MCP Server** (hỏi Claude) |
| Test complex queries | **pgAdmin Query Tool** |

---

## ⚠️ Common Issues

### Issue: `psycopg2: could not connect to server`

```bash
# Kiểm tra PostgreSQL chạy không
docker-compose ps

# Nếu không chạy
docker-compose up -d

# Nếu vẫn lỗi, check logs
docker-compose logs postgres
```

### Issue: pgAdmin không kết nối được

```
Khi tạo server, **NHẤT ĐỊNH** dùng "postgres" làm hostname,
không phải "localhost"!

Vì pgAdmin chạy trong container, nên nó cần tên container,
không phải localhost.
```

### Issue: `relation "users" does not exist`

```bash
# Model tồn tại nhưng table chưa được tạo trong DB
# → Cần chạy migration

alembic revision --autogenerate -m "Create users table"
alembic upgrade head
```

---

## 📖 Thêm Tài Liệu

- 📄 `PGADMIN_SETUP.md` - Chi tiết cài đặt & Best Practices
- 📄 `QUERY_EXAMPLES.md` - Các query patterns khác nhau
- 📄 `ROUTER_EXAMPLE.py` - Full example router
- 📄 `MCP_PGADMIN_INTEGRATION.md` - Dùng MCP server để query

---

## ✅ Checklist (Lần Đầu)

- [ ] Chạy `docker-compose up -d`
- [ ] Kết nối pgAdmin
- [ ] Cập nhật `.env`
- [ ] Test connection (curl `/health/db`)
- [ ] Tạo migration cho models
- [ ] Chạy `alembic upgrade head`
- [ ] Tạo UserRepository
- [ ] Tạo users router
- [ ] Test API endpoints
- [ ] Xem data trong pgAdmin

---

## 🚀 Lần Tới Chỉ Cần

```bash
# Start containers
docker-compose up -d

# Run app
uvicorn app.main:create_app --factory --reload

# That's it! 🎉
```

Enjoy! 🎊
