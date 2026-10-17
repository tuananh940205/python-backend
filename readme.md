Trong `main.py` phải sử dụng

    if __name__ == "__main__":
Chạy project bằng
```python
if __name__ == "__main__":
```


Activate trên window
```sh
.venv\Scripts\activate
```

Cài sqlAchemy
```sh
pip install alembic sqlalchemy psycopg
alembic init migrations
```

Cài thư viện kiểm tra email
```bash
pip install email-validator
```

Cài pytest
```bash
pip install pytest
```

Chạy test
```shell
python -m pytest -v
```

Cài thư viện bảo mật
```powershell
pip install "pwdlib[argon2]" PyJWT python-multipart
```

Tạo secret ngẫu nhiên trong Powershell:
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```


***

Lộ trình

```
1. Python + Backend
    Python synxtax
    module/package → __name__ → import → project structure → virtual environment → dependency management
    Backend thực sự: HTTP → FastAPI → REST API
    FastAPI project architecture + Pydantic sâu hơn + Service Layer + Router + Dependency Injection
    FastAPI DI sâu hơn + Error Handling + Response
→ 2. SQL/PostgreSQL
    SQL + PostgreSQL cho Python Backend
        1. PostgreSQL là gì
        2. Database / Table / Row / Column
        3. CREATE TABLE
        4. INSERT
        5. SELECT
        6. WHERE
        7. ORDER BY
        8. GROUP BY
        9. JOIN
        10. Index
        11. Primary Key / Foreign Key
        12. Transaction
        13. PostgreSQL kết nối với Python
        14. SQLAlchemy
        15. FastAPI + PostgreSQL
→ 3. Docker/Linux/Git
→ 4. LLM API
→ 5. RAG
→ 6. Vector DB
→ 7. AI Agent/tool calling
→ 8. Deploy một AI application thực tế
```

Query Parameter và Pydantic
```
Path parameter
Query parameter
Request body
```

API backend thực tế sẽ có flow
```
    POST /chat
           │
           ▼
    ┌──────────────────┐
    │ Chat Router      │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │ Pydantic         │
    │ ChatRequest      │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │ Dependency       │
    │ Injection        │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │ Chat Service     │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │ LLM Client       │
    └────────┬─────────┘
             │
             ▼
          OpenAI/
          Local LLM
```

Router không phải Service -> Router không chứa business logic

Phần tiếp

```
    FastAPI
       ↓
    SQLAlchemy
       ↓
    PostgreSQL
```
SQLAlchemy là ORM/database toolkit.

Sau này ta sẽ viết

    user = User(
        name="Tuan",
        age=30
    )
    
    db.add(user)
    db.commit()

AI engineer cần hiểu SQL để làm việc với
```
RAG
Data pipeline
Analytics
Vector metadata
User data
Conversation history
AI evaluation
```

MCP
```toml
cấu hình MCP hiện đã stage tham chiếu tới file này.
```

Kiến trúc mới
```
Router — API layer
HTTP, status code, request/response
     │
     ▼
Service Layer
Nghiệp vụ: quy tắc, kiểm tra, điều phối
     │
     ▼
Repository Layer
Truy vấn và thao tác dữ liệu qua SQLAlchemy
     │
     ▼
PostgreSQL
```

Vai trò từng lớp:

Lớp | Chịu trách nhiệm | Không nên làm
|-|-|-|
Router | HTTP request/response | Chứa nghiệp vụ phức tạp
Service | Quy tắc nghiệp vụ, điều phối transaction | Phụ thuộc vào chi tiết HTTP
Repository | Truy vấn dữ liệu | Quyết định quy tắc nghiệp vụ
Database | Lưu trữ và bảo đảm ràng buộc dữ liệu | Thay thế toàn bộ validation nghiệp vụ


## Alembic migrations (PowerShell)

Set `DATABASE_URL` in the active PowerShell session, replacing the username,
password, and database name with the values for your local PostgreSQL server.
Do not commit the connection URL or share it if it contains a password.

```powershell
$env:DATABASE_URL = "postgresql+psycopg://<user>:<password>@localhost:5432/<database>"
alembic revision --autogenerate -m "create users table"
alembic upgrade head
```

The `User` SQLAlchemy model defines `id`, `name`, and a timezone-aware
`created_at` column with a database-side current-time default. Alembic uses
this model's metadata to generate the migration.

## PostgreSQL MCP for VS Code

pgAdmin 4 is a PostgreSQL client, not an MCP server. The VS Code MCP server
connects directly to the PostgreSQL instance managed through pgAdmin.

Add a `MCP_DATABASE_URL` entry to the existing, gitignored `.env` file. Use the
same PostgreSQL host, port, database, username, and password shown in pgAdmin,
but use the `postgresql://` scheme (not SQLAlchemy's `postgresql+psycopg://`
scheme):

```dotenv
MCP_DATABASE_URL=postgresql://<user>:<password>@localhost:5432/python_backend
```

Replace the placeholders with the real PostgreSQL credentials. URL-encode
special characters in the username or password. Do not commit `.env` or send
the connection URL to the coding agent.

The workspace MCP configuration in `.vscode/mcp.json` starts DBHub with
`dbhub.toml`. The `execute_sql` tool is configured as read-only and capped at
500 returned rows. Use a least-privilege PostgreSQL account and a development
database; the MCP read-only setting is an additional guard, not a substitute
for database permissions.

Install Node.js 22.5 or newer if it is not already available, then restart VS
Code. Open the Command Palette and run **MCP: List Servers**, start `postgres`,
and trust the server only after reviewing its configuration. In Copilot Chat,
use **Configure Tools** to enable its database tools. For example, ask the
agent to list tables in the `public` schema or inspect the columns of `users`.
