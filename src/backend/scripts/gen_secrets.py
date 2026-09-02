"""Sinh khóa bí mật cho .env (FERNET/HMAC/JWT). Dùng cho ai muốn khóa riêng;
giá trị dev mặc định đã có sẵn trong .env.example để chạy demo ngay."""
import secrets

from cryptography.fernet import Fernet


def main() -> None:
    print("FERNET_KEY=" + Fernet.generate_key().decode())
    print("HMAC_KEY=" + secrets.token_urlsafe(32))
    print("JWT_SECRET=" + secrets.token_urlsafe(32))


if __name__ == "__main__":
    main()
