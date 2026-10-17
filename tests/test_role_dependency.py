from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth_dependencies import get_current_user
from app.authorization import require_role
from app.models import User

test_app = FastAPI()

@test_app.get("/admin-only")
def admin_only(
    user: User = Depends(require_role("admin")),
):
    return {"message": "welcome admin"}

def make_user(role: str) -> User:
    return User(
        id=1,
        name="Test User",
        email="test@example.com",
        age=30,
        role=role,
    )

def test_admin_is_allowed():
    test_app.dependency_overrides[get_current_user] = (
        lambda: make_user("admin")
    )

    try:
        response = TestClient(test_app).get("/admin-only")
        assert response.status_code == 200
        assert response.json() == {"message": "welcome admin"}
    finally:
        test_app.dependency_overrides.clear()


def test_user_is_forbidden():
    test_app.dependency_overrides[get_current_user] = (
        lambda: make_user("user")
    )

    try:
        response = TestClient(test_app).get("/admin-only")
        assert response.status_code == 403
    finally:
        test_app.dependency_overrides.clear()