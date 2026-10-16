# PostgreSQL Query Examples - Hướng Dẫn Chi Tiết

## 1. Cấu Trúc Project

```
app/
├── repositories/
│   ├── __init__.py
│   ├── base.py               # Base class cho tất cả repositories
│   ├── user_repository.py    # User-specific queries
│   └── product_repository.py # Product-specific queries
├── services/
│   ├── __init__.py
│   └── database.py           # Database utilities
├── routers/
│   ├── __init__.py
│   └── users.py              # API endpoints
└── main.py
```

---

## 2. Cách Hoạt Động

### Flow 1: GET user by ID

```
HTTP Request (GET /users/1)
         ↓
FastAPI Router
         ↓
Dependency: get_db()
         ↓
UserRepository(db).read_by_id(1)
         ↓
SQLAlchemy Query
         ↓
PostgreSQL SELECT
         ↓
JSON Response
```

### Flow 2: CREATE user

```
HTTP Request (POST /users)
         ↓
FastAPI Router + Validation
         ↓
UserRepository(db).create(obj_in)
         ↓
SQLAlchemy INSERT
         ↓
PostgreSQL INSERT
         ↓
COMMIT + REFRESH
         ↓
JSON Response
```

---

## 3. Repository Pattern - Chi Tiết

### 3.1 Base Repository (app/repositories/base.py)

```python
class BaseRepository(Generic[T]):
    def __init__(self, db: Session, model: Type[T]):
        self.db = db
        self.model = model
    
    # CRUD operations
    def create(self, obj_in: dict) -> T
    def read_by_id(self, id: int) -> Optional[T]
    def read_all(self, skip: int = 0, limit: int = 10) -> List[T]
    def update(self, id: int, obj_in: dict) -> Optional[T]
    def delete(self, id: int) -> bool
```

**Ưu điểm:**
- ✅ Không cần lặp code CRUD cơ bản
- ✅ Generic → dùng được cho mọi model
- ✅ Dễ test

### 3.2 User Repository (app/repositories/user_repository.py)

```python
class UserRepository(BaseRepository[User]):
    def get_by_email(self, email: str) -> User | None
    def get_active_users(self) -> list[User]
    def search_users(self, keyword: str) -> list[User]
    def count_users(self) -> int
```

**Quy tắc:**
- Kế thừa từ `BaseRepository[User]`
- Thêm business-specific queries
- Dùng `self.db` và `self.model` từ parent

---

## 4. Các Query Patterns

### Pattern 1: Simple SELECT

```python
# Repository method
def get_by_email(self, email: str) -> User | None:
    return self.db.query(User).filter(User.email == email).first()

# SQL tương đương
SELECT * FROM users WHERE email = :email LIMIT 1;

# Sử dụng
user = UserRepository(db).get_by_email("user@example.com")
```

### Pattern 2: SELECT with WHERE conditions

```python
# Repository method
def get_active_users(self, skip: int = 0, limit: int = 10) -> list[User]:
    return self.db.query(User).filter(
        User.is_active == True
    ).offset(skip).limit(limit).all()

# SQL tương đương
SELECT * FROM users 
WHERE is_active = true 
OFFSET :skip 
LIMIT :limit;

# Sử dụng
active_users = UserRepository(db).get_active_users(skip=0, limit=10)
```

### Pattern 3: LIKE search

```python
# Repository method
def search_users(self, keyword: str) -> list[User]:
    return self.db.query(User).filter(
        (User.name.ilike(f"%{keyword}%")) |
        (User.email.ilike(f"%{keyword}%"))
    ).all()

# SQL tương đương
SELECT * FROM users 
WHERE name ILIKE :keyword OR email ILIKE :keyword;

# Sử dụng
results = UserRepository(db).search_users("john")
```

### Pattern 4: COUNT aggregation

```python
# Repository method
def count_users(self) -> int:
    return self.db.query(func.count(User.id)).scalar()

# SQL tương đương
SELECT COUNT(id) FROM users;

# Sử dụng
total = UserRepository(db).count_users()
```

### Pattern 5: GROUP BY + aggregation

```python
# Repository method
def count_users_by_role(self) -> dict:
    results = self.db.query(
        User.role,
        func.count(User.id).label('count')
    ).group_by(User.role).all()
    return [{"role": r[0], "count": r[1]} for r in results]

# SQL tương đương
SELECT role, COUNT(id) as count 
FROM users 
GROUP BY role;
```

### Pattern 6: JOIN multiple tables

```python
# Giả sử User có relationship với Post
# Repository method
def get_users_with_posts(self):
    from models.post import Post
    return self.db.query(User).join(Post).filter(
        Post.published == True
    ).all()

# SQL tương đương
SELECT DISTINCT u.* FROM users u
JOIN posts p ON u.id = p.user_id
WHERE p.published = true;
```

### Pattern 7: Raw SQL query (khi cần)

```python
# DatabaseService method
@staticmethod
def execute_raw_query(db: Session, query: str, params: Dict = None):
    if params is None:
        params = {}
    result = db.execute(text(query), params)
    columns = result.keys()
    return [dict(zip(columns, row)) for row in result.fetchall()]

# Sử dụng
query = """
    SELECT u.id, u.name, COUNT(p.id) as post_count
    FROM users u
    LEFT JOIN posts p ON u.id = p.user_id
    GROUP BY u.id
    ORDER BY post_count DESC
"""
results = DatabaseService.execute_raw_query(db, query)
```

---

## 5. API Router Example

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

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    username: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CREATE
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    if repo.get_by_email(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    return repo.create(user.dict())

# READ by ID
@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user = repo.read_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

# READ all
@router.get("/", response_model=list[UserResponse])
def list_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    return repo.read_all(skip, limit)

# SEARCH
@router.get("/search/{keyword}", response_model=list[UserResponse])
def search_users(keyword: str, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    return repo.search_users(keyword)

# UPDATE
@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user: UserCreate, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    updated = repo.update(user_id, user.dict())
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return updated

# DELETE
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    if not repo.delete(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
```

---

## 6. Testing Examples

### Test CREATE

```bash
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","email":"john@example.com","username":"johndoe"}'
```

### Test READ

```bash
curl "http://localhost:8000/users/1"
```

### Test LIST

```bash
curl "http://localhost:8000/users/?skip=0&limit=10"
```

### Test SEARCH

```bash
curl "http://localhost:8000/users/search/john"
```

### Test UPDATE

```bash
curl -X PUT "http://localhost:8000/users/1" \
  -H "Content-Type: application/json" \
  -d '{"name":"Jane Doe","email":"jane@example.com","username":"janedoe"}'
```

### Test DELETE

```bash
curl -X DELETE "http://localhost:8000/users/1"
```

---

## 7. Transaction & Error Handling

### Atomicity

```python
def transfer_money(db: Session, from_id: int, to_id: int, amount: float):
    try:
        # Tất cả queries trong try block sẽ được atomic (tất cả hoặc không)
        from_user = db.query(User).filter(User.id == from_id).first()
        to_user = db.query(User).filter(User.id == to_id).first()
        
        if from_user.balance < amount:
            raise ValueError("Insufficient balance")
        
        from_user.balance -= amount
        to_user.balance += amount
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()  # Hoàn tác tất cả changes
        raise
```

---

## 8. Performance Tips

| Tip | Giải Thích |
|-----|-----------|
| Dùng `select()` từ sqlalchemy 2.0 | Có thể dùng typing hints |
| Lazy load vs Eager load | Dùng `joinedload()` để tránh N+1 queries |
| Index keys thường query | `CREATE INDEX idx_email ON users(email)` |
| Paginate large results | Dùng `.offset().limit()` |
| Use connection pool | `pool_pre_ping=True` trong engine |

---

## 9. Next Steps Sau Khi Làm Xong

- [ ] Tạo migration files cho models
- [ ] Chạy `alembic upgrade head`
- [ ] Tạo seed data
- [ ] Viết unit tests cho repositories
- [ ] Setup logging
- [ ] Thêm input validation
