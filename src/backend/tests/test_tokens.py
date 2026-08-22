import jwt
import pytest

from app.security import tokens


def test_create_and_decode():
    t = tokens.create_access_token("1", "admin1", "admin")
    payload = tokens.decode_token(t)
    assert payload["sub"] == "1"
    assert payload["username"] == "admin1"
    assert payload["role"] == "admin"


def test_expired_token_rejected(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "jwt_expire_minutes", -1)
    t = tokens.create_access_token("1", "admin1", "admin")
    with pytest.raises(jwt.ExpiredSignatureError):
        tokens.decode_token(t)
