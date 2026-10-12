import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# đọc các biến môi trường từ file .env.
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL chưa được cấu hình trong file .env")
# tạo engine quản lý kết nối đến PostgreSQL.
# engine không đồng nghĩa với việc luôn mở một kết nối duy nhất.
# SQLAlchemy quản lý các kết nối thông qua connection pool.
engine = create_engine(
    DATABASE_URL,
    # in các câu SQL do SQLAlchemy thực thi ra terminal, rất hữu ích khi học.
    echo=True,
)
# factory dùng để tạo các database session.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

# lớp nền để các ORM Model kế thừa và khai báo cấu trúc bảng.
class Base(DeclarativeBase):
    pass