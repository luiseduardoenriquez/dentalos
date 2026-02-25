from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ──────────────────────────────────
    environment: str = "development"
    debug: bool = False
    app_name: str = "DentalOS"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    allowed_hosts: str = "localhost,127.0.0.1"

    # ─── Server ───────────────────────────────────────
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8000
    workers: int = 1

    # ─── Database ─────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://dentalos:dentalos_dev_password@localhost:5432/dentalos_dev"
    )
    database_sync_url: str = (
        "postgresql+psycopg://dentalos:dentalos_dev_password@localhost:5432/dentalos_dev"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_echo: bool = False

    # ─── Redis ────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ─── RabbitMQ ─────────────────────────────────────
    rabbitmq_url: str = "amqp://dentalos:dentalos_dev_password@localhost:5672/dentalos"
    sync_queue: bool = True

    # ─── Authentication (JWT) ─────────────────────────
    secret_key: str = "dev-secret-key-change-in-production-immediately"  # noqa: S105
    jwt_secret: str = "dev-jwt-secret-change-in-production-immediately"  # noqa: S105
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # ─── CORS ─────────────────────────────────────────
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # ─── File Storage (S3 / MinIO) ────────────────────
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "dentalos_minio"
    s3_secret_key: str = "dentalos_minio_password"  # noqa: S105
    s3_bucket_name: str = "dentalos-dev"
    s3_region: str = "us-east-1"

    # ─── Sentry ───────────────────────────────────────
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.0
    sentry_environment: str = "development"


settings = Settings()
