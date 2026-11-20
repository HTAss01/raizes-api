"""Engine, sessão e dependência de banco."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.is_sqlite else {}

engine: Engine = create_engine(
    settings.database_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args=connect_args,
)


if settings.is_sqlite:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # pragma: no cover
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Dependência FastAPI: uma sessão por request, sempre fechada."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session() -> Session:
    """Sessão avulsa para scripts (ex.: seed)."""

    return SessionLocal()
