Mục tiêu chuyển từ
```
Client
  ↓
main.py
  ↓
Business logic
  ↓
Database / AI
```
sang:
```
Client
   ↓
Router
   ↓
Service
   ↓
Repository / Database / AI
```

Chúng ta sẽ tổ chức thành
```
python-backend/
│
├── .venv/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   └── chat.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   └── chat_service.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── chat.py
│   │
│   └── models/
│       ├── __init__.py
│       └── user.py
│
└── pyproject.toml
```