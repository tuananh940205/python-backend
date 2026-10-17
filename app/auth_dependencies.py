import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session
from starlette.status import HTTP_401_UNAUTHORIZED

from app.dependencies import get_db
from app.models import User
from app.security import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        subject = payload.get("sub")

        if not isinstance(subject, str):
            raise credentials_error

        user_id = int(subject)
    except (InvalidTokenError, ValueError, TypeError):
        raise credentials_error

    user = db.get(User, user_id)

    if user is None:
        raise credentials_error

    return user
