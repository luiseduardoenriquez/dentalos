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
    database_pool_size: int = 25
    database_max_overflow: int = 50
    database_echo: bool = False

    # ─── Redis ────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ─── RabbitMQ ─────────────────────────────────────
    rabbitmq_url: str = "amqp://dentalos:dentalos_dev_password@localhost:5672/dentalos"
    sync_queue: bool = True

    # ─── Authentication (JWT RS256) ─────────────────────
    secret_key: str = "dev-secret-key-change-in-production-immediately"  # noqa: S105
    jwt_private_key_path: str = "keys/private.pem"
    jwt_public_key_path: str = "keys/public.pem"
    jwt_key_id: str = "dentalos-key-1"
    jwt_algorithm: str = "RS256"
    jwt_issuer: str = "dentalos-api"
    jwt_audience: str = "dentalos-api"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # ─── Password ────────────────────────────────────
    password_bcrypt_rounds: int = 12
    password_pepper: str = ""  # noqa: S105
    lockout_threshold: int = 5
    lockout_duration_minutes: int = 15

    # ─── Tenant ──────────────────────────────────────
    tenant_schema_prefix: str = "tn_"

    # ─── CORS ─────────────────────────────────────────
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    # ─── File Storage (S3 / MinIO) ────────────────────
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "dentalos_minio"
    s3_secret_key: str = "dentalos_minio_password"  # noqa: S105
    s3_bucket_name: str = "dentalos-dev"
    s3_region: str = "us-east-1"

    # ─── ClamAV Virus Scanning ────────────────────────
    # Set to the Unix socket path to enable scanning (e.g. /var/run/clamav/clamd.ctl).
    # Leave empty to disable (fail-open — see virus_scan.py).
    clamav_socket: str = ""

    # ─── Email (SendGrid) ──────────────────────────────
    sendgrid_api_key: str = ""
    email_from_name: str = "DentalOS"
    email_from_address: str = "noreply@dentalos.app"
    frontend_url: str = "http://localhost:3000"

    # ─── Sentry ───────────────────────────────────────
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.0
    sentry_environment: str = "development"

    # ─── Monitoring ────────────────────────────────────
    prometheus_enabled: bool = True
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # ─── MATIAS / DIAN E-Invoicing ────────────────────
    matias_client_id: str = ""
    matias_secret: str = ""
    matias_base_url: str = "https://api.matias.com.co"
    matias_environment: str = "test"  # "test" or "production"

    # ─── WhatsApp (Meta Cloud API) ───────────────────────
    whatsapp_access_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_verify_token: str = "dentalos-whatsapp-verify"
    whatsapp_phone_number_id: str = ""

    # ─── Twilio SMS ──────────────────────────────────────
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    # ─── Mercado Pago ────────────────────────────────────
    mercadopago_access_token: str = ""

    # ─── Google Calendar ─────────────────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""


settings = Settings()
