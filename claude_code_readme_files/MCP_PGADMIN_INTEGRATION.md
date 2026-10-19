# MCP Server + pgAdmin 4 Integration Guide

## 1. MCP Server là gì?

MCP (Model Context Protocol) Server cho phép Claude Code kết nối và quản lý các dịch vụ bên ngoài.

### MCP Servers có sẵn cho PostgreSQL:

| Server | Chức năng | Cài đặt |
|--------|----------|--------|
| `@anthropic-ai/mcp-server-postgres` | Query PostgreSQL trực tiếp | `npm install -g @anthropic-ai/mcp-server-postgres` |
| `@anthropic-ai/mcp-server-sqlite` | Query SQLite | `npm install -g @anthropic-ai/mcp-server-sqlite` |

---

## 2. Cài Đặt MCP Server PostgreSQL

### 2.1 Cài đặt Node.js (nếu chưa có)

```bash
# Kiểm tra version
node --version

# Nếu chưa có, download từ https://nodejs.org/
```

### 2.2 Cài MCP Server PostgreSQL

```bash
npm install -g @anthropic-ai/mcp-server-postgres
```

### 2.3 Cấu hình trong Claude Code

Tạo hoặc edit `~/.claude/settings.json` (hoặc `~/.claude/settings.local.json`):

```json
{
  "mcpServers": {
    "postgres": {
      "command": "node",
      "args": [
        "-e",
        "require('@anthropic-ai/mcp-server-postgres').run()"
      ],
      "env": {
        "PGHOST": "localhost",
        "PGPORT": "5432",
        "PGUSER": "postgres",
        "PGPASSWORD": "your_password",
        "PGDATABASE": "python_backend"
      }
    }
  }
}
```

### 2.4 Restart Claude Code

```bash
# Trong terminal của Claude Code
/reload-mcp
```

---

## 3. Lợi Ích của MCP Server PostgreSQL

✅ **Query PostgreSQL trực tiếp từ Claude Code**
```
Bạn có thể hỏi Claude: 
"Cho tôi xem tất cả users trong database"
→ Claude dùng MCP server để query PostgreSQL
→ Nhận kết quả trực tiếp
```

✅ **Không cần viết SQL thủ công**
```
Claude Code có thể:
- Tạo migrations
- Inspect schema
- Run queries
- Debug database issues
```

✅ **Tích hợp với development workflow**
```
Khi bạn:
- Thêm model mới
- Thay đổi schema
- Cần kiểm tra dữ liệu
→ Claude tương tác trực tiếp với database
```

---

## 4. Sử Dụng MCP Server

### 4.1 Hỏi Claude về Database

```
Prompt: "Mô tả schema của bảng users"
→ Claude dùng MCP → Query information_schema
→ Trả về: Column names, types, constraints

Prompt: "Có bao nhiêu active users?"
→ Claude dùng MCP → SELECT COUNT(*) FROM users WHERE is_active=true
→ Trả về: 42

Prompt: "Tạo index cho email column"
→ Claude dùng MCP → CREATE INDEX idx_email ON users(email)
→ Trả về: Success
```

### 4.2 Workflow Example

```
1. Bạn tạo model mới:
   class Product(Base):
       name: str
       price: float

2. Bạn hỏi Claude:
   "Tạo migration cho Product model"
   
3. Claude:
   - Kiểm tra schema hiện tại (via MCP)
   - Tạo migration file
   - Chạy alembic upgrade (via MCP)
   - Verify schema (via MCP)
```

---

## 5. So Sánh: MCP vs pgAdmin vs Repository Pattern

| Việc cần làm | MCP Server | pgAdmin 4 | Repository Pattern |
|-------------|-----------|----------|-------------------|
| Query từ CLI | ✅ | ❌ | ❌ (Python code) |
| UI để quản lý | ❌ | ✅✅✅ | ❌ |
| Tạo migration | ✅ | ❌ | ❌ |
| Dùng trong code | ❌ | ❌ | ✅✅✅ |
| Real-time data | ✅ (live query) | ✅ | ✅ (via API) |

**Kết luận:**
- **MCP Server**: Dùng khi develop (query nhanh, debug)
- **pgAdmin**: Dùng để quản lý, visual inspection
- **Repository**: Dùng trong production code

---

## 6. Full Setup Checklist

### A. PostgreSQL + pgAdmin

- [ ] Cài Docker Desktop
- [ ] Tạo `docker-compose.yml`
- [ ] Chạy `docker-compose up -d`
- [ ] Truy cập pgAdmin ở `http://localhost:5050`
- [ ] Kết nối PostgreSQL server
- [ ] Tạo database `python_backend`

### B. MCP Server PostgreSQL

- [ ] Cài Node.js (nếu chưa)
- [ ] Chạy `npm install -g @anthropic-ai/mcp-server-postgres`
- [ ] Cập nhật `~/.claude/settings.json` với MCP config
- [ ] Restart Claude Code (`/reload-mcp`)
- [ ] Test: Hỏi Claude về database schema

### C. Repository Pattern

- [ ] Tạo `app/repositories/base.py`
- [ ] Tạo `app/repositories/user_repository.py`
- [ ] Tạo `app/services/database.py`
- [ ] Tạo router (`app/routers/users.py`) dùng repositories
- [ ] Test API endpoints

### D. Cập nhật Project Config

- [ ] Cập nhật `.env` với `DATABASE_URL`
- [ ] Tạo migration files với Alembic
- [ ] Chạy migrations: `alembic upgrade head`
- [ ] Seed dữ liệu test (tùy chọn)

---

## 7. Example Workflow

### Scenario: Thêm feature "User roles"

**Step 1: Tạo model**
```python
class User(Base):
    __tablename__ = "users"
    id: int
    name: str
    email: str
    role: str = "user"  # admin, user, guest
```

**Step 2: Tạo migration**
```bash
# Dùng Alembic hoặc hỏi Claude:
# "Tạo migration để thêm column role"
alembic revision --autogenerate -m "Add role column to users"
alembic upgrade head
```

**Step 3: Kiểm tra schema (MCP)**
```
Prompt: "Mô tả lại schema bảng users"
→ Claude query PostgreSQL via MCP
→ Xác nhận role column đã được thêm
```

**Step 4: Tạo query logic (Repository)**
```python
# app/repositories/user_repository.py
def get_users_by_role(self, role: str):
    return self.db.query(User).filter(User.role == role).all()
```

**Step 5: Tạo API endpoint (Router)**
```python
@router.get("/role/{role}")
def get_users_by_role(role: str, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    return repo.get_users_by_role(role)
```

**Step 6: Test**
```bash
curl "http://localhost:8000/users/role/admin"
# →  List of admin users
```

**Step 7: Verify trong pgAdmin**
- Mở pgAdmin
- Query: `SELECT role, COUNT(*) FROM users GROUP BY role`
- Xem distribution

---

## 8. Troubleshooting

### MCP Server không kết nối

**Error**: `Cannot connect to MCP server postgres`

**Solution**:
```bash
# 1. Kiểm tra PostgreSQL đang chạy
docker ps | grep postgres

# 2. Kiểm tra cấu hình trong settings.json
~/.claude/settings.json

# 3. Reload MCP
/reload-mcp

# 4. Check logs
# Xem logs của MCP ở notification panel
```

### pgAdmin không connect được

**Error**: `Unable to connect to server: could not connect to server`

**Solution**:
```bash
# 1. Kiểm tra container đang chạy
docker-compose ps

# 2. Kiểm tra password đúng không
# Nhập lại password khi tạo server

# 3. Dùng hostname "postgres" không phải "localhost"
# (vì dùng internal docker network)

# 4. Restart services
docker-compose down
docker-compose up -d
```

### Repository queries không work

**Error**: `AttributeError: 'User' has no attribute 'email'`

**Solution**:
```python
# 1. Kiểm tra model đã định nghĩa column
# models/user.py: email: str

# 2. Kiểm tra column tồn tại trong database
# (chạy migration)

# 3. Kiểm tra model import đúng
from models.user import User
```

---

## 9. Performance Tips

### Indexes

```python
# models/user.py
class User(Base):
    __tablename__ = "users"
    id: int = Column(Integer, primary_key=True)
    email: str = Column(String, unique=True, index=True)
    username: str = Column(String, unique=True, index=True)
```

### Pagination

```python
# Luôn luôn paginate large queries
def list_users(skip: int = 0, limit: int = 10):
    return repo.read_all(skip=skip, limit=limit)
```

### Lazy Loading

```python
# Tránh N+1 problem
from sqlalchemy.orm import joinedload

def get_users_with_posts(db: Session):
    return db.query(User).options(joinedload(User.posts)).all()
```

---

## 10. Learning Path

```
Week 1: Setup & Docker
  Day 1: Cài PostgreSQL + pgAdmin via Docker
  Day 2: Kết nối pgAdmin, tạo DB
  Day 3: Cập nhật .env, test connection

Week 2: MCP Server
  Day 4: Cài MCP Server PostgreSQL
  Day 5: Cấu hình Claude Code
  Day 6: Practice queries via MCP
  Day 7: Debug issues

Week 3: Repository Pattern
  Day 8-9: Tạo BaseRepository
  Day 10: Tạo UserRepository
  Day 11-12: Tạo API endpoints
  Day 13-14: Test & debugging

Week 4: Advanced
  Day 15-16: Transactions & error handling
  Day 17-18: Performance optimization
  Day 19-20: Unit tests
```

---

## Liên Kết & Tài Liệu

- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **SQLAlchemy ORM**: https://docs.sqlalchemy.org/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Alembic Migrations**: https://alembic.sqlalchemy.org/
- **pgAdmin 4**: https://www.pgadmin.org/docs/pgadmin4/
