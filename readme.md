Trong `main.py` phải sử dụng

    if __name__ == "__main__":
Chạy project bằng

    if __name__ == "__main__":

Activate trên window
```
.venv\Scripts\activate
```

Cài sqlAchemy
```
pip install alembic sqlalchemy psycopg
alembic init migrations
```

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
