from app.security import passwords


def test_hash_differs_and_verifies():
    h = passwords.hash_password("secret123")
    assert h != "secret123"
    assert passwords.verify_password("secret123", h) is True
    assert passwords.verify_password("wrong", h) is False
