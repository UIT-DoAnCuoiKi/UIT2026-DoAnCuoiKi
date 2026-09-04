from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://parking:parking@localhost:5432/parking"
    fernet_key: str = ""          # bắt buộc set ở runtime, sinh bằng Fernet.generate_key()
    hmac_key: str = ""            # bắt buộc set ở runtime
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 480
    image_storage_dir: str = "./data/images"
    retention_days: int = 30
    edge_api_key: str = "edge-dev-key"
    inference_engine: str = "fake"   # fake | ml
    admin_username: str = "admin"
    admin_password: str = ""
    # Origin của dashboard được phép gọi API (CORS). Nhiều origin phân tách bằng dấu phẩy.
    cors_origins: str = (
        "http://localhost:8080,http://localhost:5173,"
        "http://127.0.0.1:8080,http://127.0.0.1:5173"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
