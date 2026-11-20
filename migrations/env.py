"""Ambiente de migrations do Alembic.

A URL do banco vem de app.config (variável DATABASE_URL), nunca do .ini,
para que SQLite e PostgreSQL usem exatamente a mesma configuração da API.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.infrastructure.db.base import Base
from app.infrastructure.db import models  # noqa: F401 - registra as tabelas no metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def _configure(connection=None, url: str | None = None) -> None:
    options = {
        "target_metadata": target_metadata,
        "compare_type": True,
        "compare_server_default": True,
        "render_as_batch": settings.is_sqlite,
        "include_schemas": False,
    }
    if connection is not None:
        context.configure(connection=connection, **options)
    else:
        context.configure(url=url, literal_binds=True, dialect_opts={"paramstyle": "named"}, **options)


def run_migrations_offline() -> None:
    _configure(url=settings.database_url)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
