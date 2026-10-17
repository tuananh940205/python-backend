from http.client import HTTPException

from fastapi import APIRouter, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.auth_schemas import RegisterRequest, TokenResponse
from app.models import User
from app.dependencies import get_db
from app.security import hash_password, verify_password, create_access_token

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

    token = create_access_token(user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
    }

