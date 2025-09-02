import secrets
from typing import Annotated

from pydantic import (
    AnyUrl,
    BeforeValidator,
    computed_field,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    # API Configuration
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days

    # Server Configuration
    SERVER_NAME: str = "SecureScribeBE"
    SERVER_HOST: str = "http://localhost"
    SERVER_PORT: int = 8000

    # CORS Configuration
    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str,
        BeforeValidator(lambda x: x.split(",") if isinstance(x, str) else x),
    ] = []

    # Project Configuration
    PROJECT_NAME: str = "SecureScribeBE"

    # Database Configuration
    POSTGRES_SERVER: str = "160.191.88.194"
    POSTGRES_PORT: int = 5430
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "admin123"
    POSTGRES_DB: str = "securescribe"

    # Firebase Configuration
    FIREBASE_SERVICE_ACCOUNT_KEY_PATH: str = (
        "config/keys/scribe-c7f13-firebase-adminsdk-fbsvc-1ab2f55755.json"
    )

    # Redis Configuration
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # WebSocket Configuration
    WEBSOCKET_PING_INTERVAL: int = 30     # 30 seconds
    WEBSOCKET_PING_TIMEOUT: int = 10      # 10 seconds
    WEBSOCKET_MAX_CONNECTIONS: int = 1000 # Maximum concurrent connections
    WEBSOCKET_MESSAGE_SIZE_LIMIT: int = 65536  # 64KB message limit
    WEBSOCKET_CONNECTION_TIMEOUT: int = 300    # 5 minutes inactive timeout
    WEBSOCKET_CLEANUP_INTERVAL: int = 60       # 1 minute cleanup interval

    @computed_field  # type: ignore[prop-decorator]
    @property
    def CELERY_BROKER_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @computed_field
    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> MultiHostUrl:
        return MultiHostUrl.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )


settings = Settings()
