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
    admin_username: str = "admin"
    admin_password: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
