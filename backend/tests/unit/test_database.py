
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Task
from app.db.session import Base, build_session_factory


def test_database_base_can_create_task_table_in_memory() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    try:
        Base.metadata.create_all(engine)

        assert "tasks" in Base.metadata.tables

        with engine.connect() as connection:
            assert connection.dialect.has_table(connection, "tasks")
    finally:
        engine.dispose()


def test_session_factory_creates_a_session() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    session_factory = build_session_factory(engine)

    try:
        with session_factory() as session:
            assert isinstance(session, Session)
    finally:
        engine.dispose()


def test_task_model_has_expected_columns() -> None:
    assert set(Task.__table__.columns.keys()) == {
        "id",
        "description",
        "repository_url",
        "status",
        "created_at",
        "updated_at",
    }
