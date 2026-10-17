<p align="center" style="font-size: 30px">
    <b>
        Refresh Token, đăng xuất và thu hồi phiên đăng nhập trong FastAPI
    </b>
</p>

Ở bài trước, bạn đã xây dựng Authentication bằng JWT Access Token và Authorization bằng RBAC.  
Hôm nay, chúng ta nâng cấp hệ thống đăng nhập để xử lý các tình huống thực tế: access token hết hạn, người dùng đăng xuất, đăng nhập trên nhiều thiết bị và thu hồi phiên đăng nhập.

# 1. Vấn đề của hệ thống hiện tại
Hiện tại, API của bạn cấp một JWT khi người dùng đăng nhập. JWT có thời hạn, ví dụ 30 phút.
Loại token | Đặc điểm
|-|-|
Access Token | Dùng để gọi API được bảo vệ, có thời hạn ngắn.
Refresh Token | Dùng để xin Access Token mới mà không bắt người dùng đăng nhập lại.

Nếu chỉ sử dụng Access Token dạng JWT, khi token đã được phát hành thì server thường không thể thu hồi riêng token đó ngay lập tức nếu không kiểm tra thêm trạng thái phía server.

Chúng ta sẽ sử dụng thiết kế sau:
- Access Token: JWT, hiệu lực 30 phút.
- Refresh Token: chuỗi ngẫu nhiên khó đoán, hiệu lực 7 ngày.
- Database: lưu mã băm của Refresh Token để có thể thu hồi phiên.
- Token Rotation: mỗi lần refresh thành công, Refresh Token cũ bị thay thế bằng token mới.

Đây là thiết kế thực hành phù hợp để hiểu cơ chế session trong backend.  
Khi triển khai thực tế, thời hạn và cách lưu token cần điều chỉnh theo mức độ rủi ro của ứng dụng.

# 2. Luồng hoạt động
                      1. Login
            Kiểm tra email và password
                          ↓
                 2. Cấp hai token
             Access Token + Refresh Token
                          ↓
                     3. Gọi API
     Gửi Access Token trong Authorization: Bearer
                          ↓
              4. Access Token hết hạn
       Gửi Refresh Token tới POST /auth/refresh
                          ↓
                  5. Cấp token mới
Refresh Token cũ bị vô hiệu hóa bằng cơ chế xoay token

Các endpoint chúng ta sẽ xây dựng:
Endpoint | Chức năng
|-|-|
POST /auth/login | Đăng nhập, tạo phiên và cấp hai token
POST /auth/refresh | Cấp Access Token mới và xoay Refresh Token
POST /auth/logout | Thu hồi phiên hiện tại
GET /users/me | Kiểm tra người dùng đã đăng nhập

# 3. Bước 1 — Tạo bảng lưu phiên đăng nhập
Trong PostgreSQL, mở Query Tool của pgAdmin và chạy SQL sau:
```sql
CREATE TABLE auth_sessions (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INTEGER NOT NULL
        REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
);

CREATE INDEX ix_auth_sessions_user_id
ON auth_sessions(user_id);
```

Ý nghĩa các cột:
Cột | Ý nghĩa
|-|-|
user_id | Người dùng sở hữu phiên
refresh_token_hash | SHA-256 của Refresh Token, không lưu token gốc
created_at | Thời điểm tạo phiên
expires_at | Thời điểm Refresh Token hết hạn
revoked_at | Thời điểm thu hồi; NULL nghĩa là chưa bị thu hồi

Một người dùng có thể có nhiều bản ghi phiên, tương ứng với nhiều lần đăng nhập hoặc nhiều thiết bị.

## Tạo model SQLAlchemy
Thêm vào `app/models.py`. Sử dụng `Base` hiện có của dự án; không tạo thêm một Base mới.
```py
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(always=True),
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    refresh_token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
```
Nếu các import SQLAlchemy đã có trong models.py, hãy bổ sung phần còn thiếu thay vì khai báo trùng.  
Nếu đang dùng Alembic, bạn nên tạo migration cho model; vì bảng vừa được tạo bằng SQL thủ công, hãy đảm bảo migration không cố tạo lại bảng đó.

# 4. Bước 2 — Bổ sung hàm tạo Refresh Token
Mở `app/security.py`. Giữ nguyên các hàm hash password, verify password và `create_access_token()` đang hoạt động. Bổ sung:
```py
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_refresh_token() -> str:
    """Tạo token ngẫu nhiên, khó đoán."""
    return secrets.token_urlsafe(64)

def hash_refresh_token(token: str) -> str:
    """Chỉ lưu mã băm của refresh token trong database."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )
```

Vì sao dùng SHA-256 cho Refresh Token, nhưng dùng Argon2 cho password?
- Refresh Token được tạo ngẫu nhiên với entropy cao, nên SHA-256 phù hợp để tra cứu và xác minh token.
- Password do con người đặt, có thể dễ đoán; cần thuật toán hash password chuyên dụng như Argon2 để chống dò mật khẩu.

Không ghi Refresh Token gốc vào log hoặc database. Chỉ trả token gốc cho client khi cần sử dụng.

# 5. Bước 3 — Cập nhật schema phản hồi
Trong `app/auth_schemas.py`, bổ sung hoặc cập nhật `TokenResponse`:
```py
from pydantic import BaseModel, Field

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)

class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)
```
`expires_in` là thời gian sống còn lại của `Access Token`, tính bằng giây. Với cấu hình 30 phút, giá trị là 1800.

# 6. Bước 4 — Cập nhật endpoint đăng nhập
Trong `app/routers/auth.py`, khi xác thực email và password thành công, cần tạo một phiên mới và trả cả hai token.

Ví dụ phần logic phát hành token:
```py
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import AuthSession, User
from app.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)

def issue_tokens(db: Session, user: User) -> dict:
    raw_refresh_token = create_refresh_token()

    session = AuthSession(
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(raw_refresh_token),
        expires_at=refresh_token_expiry(),
    )

    db.add(session)
    db.commit()

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": raw_refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
```

Trong endpoint login hiện tại, sau khi đã tìm thấy user và xác minh password thành công, gọi:
```py
return issue_tokens(db, user)
```
Ở đây `db` là `SQLAlchemy session` và user là tài khoản vừa xác thực.  
Không gọi hàm này trước khi kiểm tra password.

Lưu ý: `issue_tokens()` là hàm hỗ trợ, không phải endpoint độc lập.  
Giữ nguyên logic kiểm tra thông tin đăng nhập đang có trong `/auth/login`.

# 7. Bước 5 — Xây dựng POST /auth/refresh
Khi `Access Token` hết hạn, client gửi `Refresh Token` tới endpoint này để lấy cặp token mới.

Thêm vào `app/routers/auth.py`:
```py
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth_schemas import RefreshRequest, TokenResponse
from app.dependencies import get_db
from app.models import AuthSession, User
from app.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)

def invalid_refresh_token() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )

@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(
    body: RefreshRequest,
    db: Session = Depends(get_db),
):
    token_hash = hash_refresh_token(body.refresh_token)

    session = db.scalar(
        select(AuthSession).where(
            AuthSession.refresh_token_hash == token_hash
        )
    )

    now = datetime.now(timezone.utc)

    if session is None:
        raise invalid_refresh_token()

    if session.revoked_at is not None or session.expires_at <= now:
        raise invalid_refresh_token()

    user = db.get(User, session.user_id)
    if user is None:
        raise invalid_refresh_token()

    # Tạo Refresh Token mới và thay hash cũ trong database.
    new_refresh_token = create_refresh_token()
    session.refresh_token_hash = hash_refresh_token(new_refresh_token)
    session.expires_at = refresh_token_expiry()

    db.commit()

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
```

Trong file này, hãy bảo đảm `router = APIRouter(prefix="/auth", ...)` đã được khai báo từ bài trước.  
Nếu đã có các import hoặc tên schema tương tự, chỉ bổ sung phần còn thiếu.

## Điều gì xảy ra khi refresh?

Ví dụ:
1. Client gửi Refresh Token R1.
2. Server băm R1, tìm phiên hợp lệ.
3. Server thay hash của R1 bằng hash của R2.
4. Server trả Access Token mới và R2.
5. Nếu client tiếp tục gửi R1, token đó không còn tìm thấy trong database nên bị từ chối.

Đó là `Refresh Token Rotation`.
```
Lưu ý bảo mật: đoạn code trên minh họa luồng cơ bản. 
Hai request refresh đồng thời có thể tạo ra race condition. 
Trong môi trường production, cần bảo đảm thao tác kiểm tra và xoay token là nguyên tử, chẳng hạn dùng transaction với khóa hàng SELECT ... FOR UPDATE hoặc cập nhật có điều kiện. 
Hệ thống nhạy cảm còn cần chính sách phát hiện token cũ bị sử dụng lại và thu hồi phiên hoặc cả nhóm token liên quan.
```

# 8. Bước 6 — Xây dựng `POST /auth/logout`

Đăng xuất cần thu hồi Refresh Token của phiên hiện tại.  
Thêm vào `app/routers/auth.py`:
```py
from fastapi import Response
from app.auth_schemas import LogoutRequest

@router.post("/logout", status_code=204)
def logout(
    body: LogoutRequest,
    db: Session = Depends(get_db),
):
    token_hash = hash_refresh_token(body.refresh_token)

    session = db.scalar(
        select(AuthSession).where(
            AuthSession.refresh_token_hash == token_hash
        )
    )

    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()

    return Response(status_code=204)
```

Endpoint này chủ ý trả 204 No Content cả khi token không tồn tại, nhằm tránh tiết lộ thông tin về token.  
Khi token hợp lệ, phiên được đánh dấu đã thu hồi; các lần refresh tiếp theo sẽ bị từ chối.
## Một điểm quan trọng về JWT
Đánh dấu phiên đã thu hồi không tự động vô hiệu hóa Access Token JWT đã cấp trước đó.  
Nếu Access Token vẫn còn hạn, nó có thể tiếp tục được chấp nhận bởi get_current_user() hiện tại.

Với thiết kế này, sau logout, Refresh Token không thể cấp token mới, còn Access Token cũ hết hiệu lực theo thời hạn của nó.  
Nếu cần vô hiệu hóa Access Token ngay lập tức, bạn phải bổ sung cơ chế kiểm tra trạng thái phiên hoặc denylist cho Access Token; điều đó có thể làm tăng số lần truy vấn server.

# 9. Bước 7 — Chạy thử trên Swagger UI
Khởi động FastAPI trong PowerShell tại thư mục dự án:
```
python -m uvicorn app.main:app --reload
```
Mở http://127.0.0.1:8000/docs.

Bước 1: Đăng nhập
Gọi `POST /auth/login` với email và password theo định dạng endpoint hiện tại. Xác nhận response có `access_token, refresh_token và expires_in`.

Bước 2: Gọi API cần đăng nhập
Dùng Access Token để gọi `GET /users/me`. Nếu gặp 422 với thông báo liên quan đến user_id, hãy kiểm tra thứ tự khai báo route `/users/me` và `/users/{user_id}`.

Bước 3: Refresh
Gọi `POST /auth/refresh` với body:
```json
{
  "refresh_token": "TOKEN_NHAN_DUOC_KHI_LOGIN"
}
```
Lưu lại cặp token mới. Thử gửi lại Refresh Token cũ; request phải bị từ chối.

Bước 4: Logout
Gọi `POST /auth/logout` với Refresh Token mới nhất. Sau đó thử refresh bằng token vừa thu hồi; server phải từ chối.

# 10. Những điều cần nhớ khi đưa vào production
- Client game Unity: lưu token trong nơi lưu trữ an toàn của nền tảng; tránh lưu trong PlayerPrefs vì dữ liệu ở đó không được mã hóa.
- Web frontend: cân nhắc lưu Refresh Token trong cookie HttpOnly, Secure, SameSite phù hợp và triển khai biện pháp chống CSRF khi cần.
- Đăng xuất mọi thiết bị: thu hồi tất cả session chưa bị thu hồi của user thay vì chỉ một session.
- Đổi mật khẩu hoặc khóa tài khoản: cân nhắc thu hồi toàn bộ session hiện có.
- Dọn dữ liệu: có thể định kỳ xóa các session đã hết hạn hoặc đã thu hồi sau thời gian lưu trữ cần thiết.
- Xoay token an toàn: phải xử lý request đồng thời và việc sử dụng lại token cũ.
- HTTPS: bắt buộc khi truyền thông tin đăng nhập và token qua mạng.