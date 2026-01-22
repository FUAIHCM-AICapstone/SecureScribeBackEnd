import secrets
from typing import Annotated

from pydantic import (
    AnyUrl,
    BeforeValidator,
    computed_field,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.vault_loader import load_config

load_config()


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
    SERVER_PORT: int = 8081

    # CORS Configuration
    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str,
        BeforeValidator(lambda x: x.split(",") if isinstance(x, str) else x),
    ] = []

    # Project Configuration
    PROJECT_NAME: str = "SecureScribeBE"

    # Database Configuration
    MYSQL_SERVER: str = "db"  # External database server
    MYSQL_PORT: int = 3306  # External database port
    MYSQL_USER: str = "admin"
    MYSQL_PASSWORD: str = "admin123"
    MYSQL_DB: str = "securescribe"

    # Azure OAuth Configuration
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    AZURE_TENANT_ID: str = ""
    AZURE_REDIRECT_URI: str = "http://localhost:8081/api/v1/auth/azure/callback"
    AZURE_SCOPE: str = "User.Read"

    # Redis Configuration
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # WebSocket Configuration
    WEBSOCKET_PING_INTERVAL: int = 30  # 30 seconds
    WEBSOCKET_PING_TIMEOUT: int = 10  # 10 seconds
    WEBSOCKET_MAX_CONNECTIONS: int = 1000  # Maximum concurrent connections
    WEBSOCKET_MESSAGE_SIZE_LIMIT: int = 65536  # 64KB message limit
    WEBSOCKET_CONNECTION_TIMEOUT: int = 300  # 5 minutes inactive timeout
    WEBSOCKET_CLEANUP_INTERVAL: int = 60  # 1 minute cleanup interval

    # Throttling Configuration
    THROTTLING_ENABLED: bool = True
    THROTTLING_WINDOW_SECONDS: int = 10
    THROTTLING_MAX_REQUESTS_API: int = 30
    THROTTLING_MAX_REQUESTS_HEALTH: int = 100
    THROTTLING_MAX_REQUESTS_UPLOAD: int = 100
    THROTTLING_REDIS_KEY_PREFIX: str = "rate_limit"
    THROTTLING_CLEANUP_INTERVAL: int = 300

    # MinIO Configuration
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_NAME: str = "securescribe-files"
    MINIO_PUBLIC_BUCKET_NAME: str = "securescribe-public"
    MINIO_PUBLIC_URL: str = "http://localhost:9000"  # Public URL for permanent links (internal Docker network)
    LOG_LEVEL: str = "DEBUG"
    # File Configuration
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_FILE_EXTENSIONS: str = ".pdf,.docx,.txt,.mp3,.wav,.m4a,.webm"
    ALLOWED_MIME_TYPES: str = "application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,audio/mpeg,audio/wav,audio/mp4,audio/webm"

    # Qdrant Configuration
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6334  # gRPC port
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_NAME: str = "documents"

    # Google AI Configuration
    GOOGLE_API_KEY: str = "AIzaSyARikOBRUStNAt9zNNKoo47ReMnpXX3TH8"
    GOOGLE_EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    GOOGLE_EMBEDDING_DIMENSIONS: int = 3072  # Gemini embedding dimensions

    # Transcription API Configuration
    TRANSCRIBE_API_BASE_URL: str = "https://s2t.wc504.io.vn/api/v1"

    # Bot Service Configuration
    BOT_SERVICE_URL: str = "http://bot:3000"
    BOT_WEBHOOK_URL: str = "http://nginx/be/api/v1/bot/webhook/recording"

    # Indexing Configuration
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_CHUNKS_PER_FILE: int = 50

    # SMTP Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "Chang <noreply@meobeo.ai>"
    SMTP_RETRY_ATTEMPTS: int = 3
    SMTP_RETRY_DELAY_SECONDS: int = 5

    # OpenTelemetry Configuration
    OTEL_EXPORTER_OTLP_LOGS_ENDPOINT: str = "http://otel-collector.fpt.net/v1/logs"
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT: str = "http://otel-collector.fpt.net/v1/traces"
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT: str = "http://otel-collector.fpt.net/v1/metrics"
    OTEL_DEBUG: bool = False

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
            scheme="mysql+pymysql",
            username=self.MYSQL_USER,
            password=self.MYSQL_PASSWORD,
            host=self.MYSQL_SERVER,
            port=self.MYSQL_PORT,
            path=self.MYSQL_DB,
        )


settings = Settings()
