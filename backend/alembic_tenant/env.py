import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text
from sqlalchemy.schema import CreateSchema

from app.core.config import settings
from app.models.base import TenantBase

# Import all tenant models so metadata is populated
import app.models.tenant  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_sync_url)

target_metadata = TenantBase.metadata

SCHEMA_PATTERN = re.compile(r"^tn_[a-z0-9_]{3,40}$")


def get_tenant_schema() -> str:
    """Get the tenant schema from the -x argument."""
    schema = context.get_x_argument(as_dictionary=True).get("schema")
    if not schema:
        raise ValueError(
            "Tenant schema required: alembic -c alembic_tenant/alembic.ini "
            "upgrade head -x schema=tn_xxx"
        )
    if not SCHEMA_PATTERN.match(schema):
        raise ValueError(f"Invalid tenant schema name: {schema}")
    return schema


def run_migrations_offline() -> None:
    schema = get_tenant_schema()
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=schema,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    schema = get_tenant_schema()
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # Set search_path so all CREATE TABLE statements go to the tenant schema
        connection.execute(text(f"SET search_path TO {schema}, public"))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=schema,
            include_schemas=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
