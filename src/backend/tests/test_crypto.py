from app.security import crypto


def test_text_round_trip():
    token = crypto.encrypt_text("51F-123.45")
    assert token != "51F-123.45"
    assert crypto.decrypt_text(token) == "51F-123.45"


def test_bytes_round_trip():
    data = b"\x89PNG fake image bytes"
    token = crypto.encrypt_bytes(data)
    assert token != data
    assert crypto.decrypt_bytes(token) == data
