from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Giải thích:
# - create_engine(): tạo engine để quản lý kết nối database.
# - pool_pre_ping=True: kiểm tra kết nối trước khi sử dụng, giúp phát hiện kết nối đã mất.
# - SessionLocal: tạo các phiên làm việc với database.
# - expire_on_commit=False: giữ các thuộc tính object có thể truy cập sau khi commit mà không tự động hết hiệu lực.

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    expire_on_commit=False,
)