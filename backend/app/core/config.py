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
    api_docs_enabled: bool = True
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
    prometheus_token: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # ─── MATIAS / DIAN E-Invoicing ────────────────────
    matias_client_id: str = ""
    matias_secret: str = ""
    matias_base_url: str = "https://api.matias.com.co"
    matias_environment: str = "test"  # "test" or "production"

    # ─── Mexico SAT / PAC ──────────────────────────────
    pac_provider_url: str = ""
    pac_username: str = ""
    pac_password: str = ""
    pac_environment: str = "test"  # "test" or "production"

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

    # ─── Nequi Mobile Wallet ────────────────────────────────
    nequi_client_id: str = ""
    nequi_client_secret: str = ""
    nequi_api_key: str = ""
    nequi_base_url: str = "https://api.sandbox.nequi.com"
    nequi_webhook_secret: str = ""

    # ─── Daviplata Mobile Wallet ────────────────────────────
    daviplata_client_id: str = ""
    daviplata_client_secret: str = ""
    daviplata_base_url: str = "https://api.sandbox.daviplata.com"
    daviplata_webhook_secret: str = ""

    # ─── ADRES / BDUA (EPS Verification) ────────────────────
    adres_api_url: str = "https://api.adres.gov.co"
    adres_api_key: str = ""

    # ─── RETHUS (Professional Registry) ─────────────────────
    rethus_api_url: str = "https://www.datos.gov.co/resource"
    rethus_app_token: str = ""

    # ─── Google Calendar ─────────────────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""

    # ─── Exchange Rate API (Banco de la República) ──────────
    exchange_rate_api_url: str = "https://www.datos.gov.co/resource/32sa-8pi3.json"
    exchange_rate_api_key: str = ""

    # ─── Voice AI (STT + NLP) ─────────────────────────────
    voice_stt_provider: str = "local"  # "local" | "openai"
    voice_nlp_provider: str = "local"  # "local" | "anthropic"
    whisper_model_size: str = "base"  # "tiny" | "base" | "small" | "medium"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:32b"
    ollama_timeout_seconds: int = 120
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"
    anthropic_model_treatment: str = "claude-sonnet-4-5-20250514"
    ai_treatment_max_tokens: int = 4096
    ai_report_max_tokens: int = 1024
    voice_max_audio_bytes: int = 10 * 1024 * 1024  # 10 MB

    # ─── S29-30: Financing ──────────────────────────────────
    addi_api_key: str = ""
    addi_api_url: str = "https://api.addi.com/v1"
    sistecredito_api_key: str = ""
    sistecredito_api_url: str = "https://api.sistecredito.com/v1"
    mercadopago_webhook_secret: str = ""

    # ─── S29-30: Chatbot ────────────────────────────────────
    chatbot_model: str = "claude-haiku-4-5-20251001"
    chatbot_max_tokens: int = 512

    # ─── S29-30: Telemedicine ───────────────────────────────
    daily_api_key: str = ""
    daily_api_url: str = "https://api.daily.co/v1"

    # ─── S31-32: VoIP / Twilio Voice ───────────────────────
    twilio_voice_number: str = ""
    twilio_voice_webhook_url: str = ""

    # ─── S31-32: EPS Claims ────────────────────────────────
    eps_claims_api_url: str = ""
    eps_claims_api_key: str = ""


settings = Settings()
