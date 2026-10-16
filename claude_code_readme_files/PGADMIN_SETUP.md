# pgAdmin 4 Setup & PostgreSQL Query Guide

## 1. PostgreSQL + pgAdmin 4 Setup

### 1.1 Cài đặt PostgreSQL & pgAdmin 4 (Docker)

Tạo file `docker-compose.yml` ở root project:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: python_backend_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: your_secure_password_here
      POSTGRES_DB: python_backend
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - backend_network

  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: python_backend_pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@example.com
      PGADMIN_DEFAULT_PASSWORD: admin_password
    ports:
      - "5050:80"
    depends_on:
      - postgres
    networks:
      - backend_network

volumes:
  postgres_data:

networks:
  backend_network:
    driver: bridge
```

### 1.2 Chạy Docker Compose

```bash
docker-compose up -d
```

### 1.3 Truy cập pgAdmin 4

- **URL**: http://localhost:5050
- **Email**: admin@example.com
- **Password**: admin_password

### 1.4 Kết nối PostgreSQL trong pgAdmin

1. Mở pgAdmin → **Servers** → **Register** → **Server**
2. Nhập thông tin:
   - **Name**: python_backend (tên tùy ý)
   - **Host**: postgres (tên service trong docker)
   - **Port**: 5432
   - **Username**: postgres
   - **Password**: your_secure_password_here
   - **Database**: python_backend
3. Click **Save**

### 1.5 Cập nhật `.env` file

```env
DATABASE_URL=postgresql://postgres:your_secure_password_here@localhost:5432/python_backend
```

---

## 2. Cấu Trúc Query PostgreSQL

### 2.1 Folder Structure

```
app/
├── core/
│   └── config.py
├── db/
│   └── session.py
├── repositories/
│   ├── __init__.py
│   ├── base.py           # Base repository class
│   ├── user_repository.py
│   └── product_repository.py
├── services/
│   ├── __init__.py
│   └── database.py       # Database utilities
└── main.py
```

### 2.2 Pattern: Repository

Repository pattern giúp:
- ✅ Tách database logic khỏi business logic
- ✅ Dễ test (mock repositories)
- ✅ Tái sử dụng queries
- ✅ Dễ bảo trì

---

## 3. Cách Tạo Query

### 3.1 Base Repository Class

File: `app/repositories/base.py`

```python
from sqlalchemy.orm import Session
from typing import TypeVar, Generic, List, Optional, Type

T = TypeVar('T')

class BaseRepository(Generic[T]):
    def __init__(self, db: Session, model: Type[T]):
        self.db = db
        self.model = model

    def create(self, obj_in: dict) -> T:
        """Tạo object mới"""
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def read_by_id(self, id: int) -> Optional[T]:
        """Lấy object theo ID"""
        return self.db.query(self.model).filter(
            self.model.id == id
        ).first()

    def read_all(self, skip: int = 0, limit: int = 10) -> List[T]:
        """Lấy danh sách objects"""
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def update(self, id: int, obj_in: dict) -> Optional[T]:
        """Cập nhật object"""
        db_obj = self.read_by_id(id)
        if db_obj:
            for key, value in obj_in.items():
                setattr(db_obj, key, value)
            self.db.commit()
            self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: int) -> bool:
        """Xóa object"""
        db_obj = self.read_by_id(id)
        if db_obj:
            self.db.delete(db_obj)
            self.db.commit()
            return True
        return False
```

### 3.2 User Repository (Ví dụ)

File: `app/repositories/user_repository.py`

```python
from sqlalchemy import func
from sqlalchemy.orm import Session
from models.user import User
from app.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(db, User)

    def get_by_email(self, email: str) -> User | None:
        """Tìm user theo email"""
        return self.db.query(User).filter(User.email == email).first()

    def get_active_users(self, skip: int = 0, limit: int = 10) -> list[User]:
        """Lấy danh sách users hoạt động"""
        return self.db.query(User).filter(
            User.is_active == True
        ).offset(skip).limit(limit).all()

    def count_users(self) -> int:
        """Đếm tổng số users"""
        return self.db.query(func.count(User.id)).scalar()

    def search_users(self, keyword: str) -> list[User]:
        """Tìm users theo tên hoặc email"""
        return self.db.query(User).filter(
            (User.name.ilike(f"%{keyword}%")) |
            (User.email.ilike(f"%{keyword}%"))
        ).all()
```

### 3.3 Sử dụng Repository trong API

File: `app/routers/users.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.repositories.user_repository import UserRepository
from pydantic import BaseModel

router = APIRouter(prefix="/users", tags=["users"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class UserCreate(BaseModel):
    name: str
    email: str

@router.post("/")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Tạo user mới"""
    repo = UserRepository(db)
    
    # Kiểm tra email đã tồn tại
    if repo.get_by_email(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    return repo.create(user.dict())

@router.get("/{user_id}")
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

@router.get("/search/{keyword}")
def search_users(keyword: str, db: Session = Depends(get_db)):
    """Tìm users theo keyword"""
    repo = UserRepository(db)
    return repo.search_users(keyword)

@router.get("/")
def list_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """Lấy danh sách users"""
    repo = UserRepository(db)
    return repo.read_all(skip, limit)
```

---

## 4. SQL Raw Query (khi cần)

Khi repository pattern không đủ, sử dụng raw SQL:

```python
from sqlalchemy import text

def get_expensive_products(db: Session, min_price: int):
    """Query raw SQL"""
    query = text("""
        SELECT id, name, price 
        FROM products 
        WHERE price > :min_price 
        ORDER BY price DESC
    """)
    result = db.execute(query, {"min_price": min_price})
    return result.fetchall()
```

---

## 5. Best Practices

| ✅ Tốt | ❌ Tránh |
|--------|---------|
| Dùng Repository pattern | Để database logic ở route handlers |
| Dùng ORM (SQLAlchemy) | Dùng raw SQL quá nhiều |
| Validate data trước lưu | Lưu dữ liệu không validate |
| Xử lý exceptions rõ ràng | Không catch exceptions |
| Dùng connection pooling | Tạo connection mới mỗi query |

---

## 6. Kiểm Tra Kết Nối Database

```python
# Thêm vào app/main.py
@app.get("/health/db")
def check_db():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        value = result.scalar_one()
    return {
        "database": "connected",
        "result": value,
    }
```

Chạy:
```bash
curl http://localhost:8000/health/db
```

---

## 7. Troubleshooting

| Lỗi | Giải Pháp |
|-----|----------|
| `psycopg2: could not connect to server` | Kiểm tra PostgreSQL đang chạy |
| `No module named 'sqlalchemy'` | `pip install sqlalchemy psycopg2-binary` |
| `relation "..." does not exist` | Chạy migrations: `alembic upgrade head` |
| `pgadmin cannot connect to postgres` | Kiểm tra password & hostname (dùng `postgres` không `localhost`) |

---

## 8. Next Steps

- [ ] Cài Docker Compose
- [ ] Tạo PostgreSQL container
- [ ] Kết nối pgAdmin
- [ ] Tạo `BaseRepository` class
- [ ] Tạo repository cho mỗi model
- [ ] Migrate database
- [ ] Test API endpoints
