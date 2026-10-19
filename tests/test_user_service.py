import pytest
from app.schemas import UserCreate
from app.services import user_service

class FakeSession:
    def __init__(self, fail_commit=False):
        self.added = None
        self.committed = False
        self.rolled_back = False
        self.fail_commit = fail_commit

    def add(self, obj):
        self.added = obj

    def commit(self):
        if self.fail_commit:
            raise RuntimeError("Simulated database failure")
        self.committed = True

    def refresh(self, obj):
        obj.id = 123

    def rollback(self):
        self.rolled_back = True

def test_create_user_success(monkeypatch):
    db = FakeSession()
    payload = UserCreate(
        name="  An Nguyen  ",
        email="an@example.com",
        age=30,
    )

    def fake_add(session, user):
        session.add(user)

    monkeypatch.setattr(
        user_service.user_repository,
        "add",
        fake_add
    )

    user = user_service.create_user(db, payload)

    assert user.id == 123
    assert user.name == "An Nguyen"
    assert user.email == "an@example.com"
    assert db.committed is True
    assert db.rolled_back is False

def test_create_user_rolls_back_on_failure(monkeypatch):
    db = FakeSession(fail_commit=True)
    payload = UserCreate(
        name="An Nguyen",
        email="an@example.com",
        age=30,
    )

    monkeypatch.setattr(
        user_service.user_repository,
        "add",
        lambda session, user: session.add(user)
    )

    with pytest.raises(RuntimeError):
        user_service.create_user(db, payload)

    assert db.rolled_back is True

