import pytest
from pydantic import ValidationError

from app.schemas import UserCreate

def test_user_name_is_trimmed():
    user = UserCreate(
        name="  An Nguyen  ",
        email="an@example.com",
        age=30,
    )

    assert user.name == "An Nguyen"

def test_negative_age_is_rejected():
    with pytest.raises(ValidationError):
        UserCreate(
            name="An Nguyen",
            email="an@example.com",
            age=-1,
        )

def test_invalid_email_is_rejected():
    with pytest.raises(ValidationError):
        UserCreate(
            name="An Nguyen",
            email="not-an-email",
            age=30,
        )

def test_blank_name_is_rejected():
    with pytest.raises(ValidationError):
        UserCreate(
            name="   ",
            email="an@example.com",
            age=30,
        )