
from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy database models."""


def build_engine(database_url: str) -> Engine:
    """Create a database engine with connection health checks."""
    return create_engine(
        database_url,
        pool_pre_ping=True,
    )


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a reusable session factory."""
    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create and cache the configured database engine."""
    database_url = get_settings().database_url

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Set it in your local .env file."
        )

    return build_engine(database_url)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Return the cached session factory."""
    return build_session_factory(get_engine())


def get_db() -> Generator[Session, None, None]:
    """Provide a database session to a FastAPI request."""
    session_factory = get_session_factory()

    with session_factory() as session:
        yield session
