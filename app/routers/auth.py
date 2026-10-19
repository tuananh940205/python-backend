from datetime import datetime, timezone
from http.client import HTTPException
from fastapi import APIRouter, status, Depends, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.auth_schemas import RegisterRequest, TokenResponse, RefreshRequest, LogoutRequest
from app.models import User, AuthSession
from app.dependencies import get_db
from app.security import hash_password, verify_password, create_access_token, create_refresh_token, refresh_token_expiry, hash_refresh_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = User(
        name=payload.name.strip(),
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
    )

    if not user.name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details="Name cannot be black",
        )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email may already registered",
        ) from error

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
    }

@router.post("/login", response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    email = form.username.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if (
        user is None
        or user.password_hash is None
        or not verify_password(form.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return issue_tokens(db, user)

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