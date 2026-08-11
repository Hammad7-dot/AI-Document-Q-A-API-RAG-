"""Unit tests for password hashing and JWT helpers."""
import uuid

import pytest

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    get_subject_from_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verify_roundtrip():
    password = "super-secret-123"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_access_token_roundtrip():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)

    subject = get_subject_from_token(token, "access")

    assert subject == user_id


def test_refresh_token_wrong_type_raises():
    user_id = uuid.uuid4()
    token = create_refresh_token(user_id)

    with pytest.raises(InvalidTokenError):
        get_subject_from_token(token, "access")


def test_garbage_token_raises():
    with pytest.raises(InvalidTokenError):
        get_subject_from_token("not-a-real-token", "access")
