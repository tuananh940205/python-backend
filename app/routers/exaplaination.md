Dependency injection
```
FastAPI DI
   │
   ├── Database
   ├── Redis
   ├── Logger
   └── Config
         ↓
    UserService
         ↓
      Router
```

Kiến trúc hiện tại
```
                    HTTP Request
                         │
                         ▼
                ┌─────────────────┐
                │     Router      │
                │   users.py      │
                └────────┬────────┘
                         │
                         │ Depends()
                         ▼
                ┌─────────────────┐
                │  UserService    │
                │ user_service.py │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Database / AI   │
                │    (sau này)    │
                └─────────────────┘
```
Đường đi của dữ liệu
```
                    JSON
                     │
                     ▼
                    Pydantic Schema
                     │
                     ▼
                    Router
                     │
                     ▼
                    Service
                     │
                     ▼
                    Database / AI
```
