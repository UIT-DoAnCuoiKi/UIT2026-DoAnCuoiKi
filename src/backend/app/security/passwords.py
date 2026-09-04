import bcrypt

# bcrypt giới hạn mật khẩu 72 byte; cắt trước để tránh ValueError với bcrypt mới.
_MAX = 72


def hash_password(plaintext: str) -> str:
    pw = plaintext.encode("utf-8")[:_MAX]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plaintext: str, hashed: str) -> bool:
    pw = plaintext.encode("utf-8")[:_MAX]
    try:
        return bcrypt.checkpw(pw, hashed.encode("utf-8"))
    except ValueError:
        return False
