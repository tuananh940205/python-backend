from fastapi.testclient import TestClient

from app.main import app
from app.auth_dependencies import get_current_user
from app.models import User

def make_user(user_id: int, role: str) -> User:
    return User(
        id=user_id,
        name="Test User",
        email="test@example.com",
        age=30,
        role=role,
    )

def test_admin_can_access_admin_endpoint():
    app.dependency_overrides[get_current_user] = (
        lambda: make_user(1, "admin")
    )

    try:
        client = TestClient(app)
        response = client.get("/admin/users")

        # Endpoint còn cần database để lấy danh sách.
        # Test quyền nên tách phần kiểm tra role khỏi truy vấn DB.
        assert response.status_code != 403
    finally:
        app.dependency_overrides.clear()

def test_regular_user_is_forbidden():
    app.dependency_overrides[get_current_user] = (
        lambda: make_user(2, "user")
    )

    try:
        client = TestClient(app)
        response = client.get("/admin/users")

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
