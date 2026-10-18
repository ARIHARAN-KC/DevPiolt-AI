
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.session import Base, build_session_factory, get_db
from app.main import app

# Share one in-memory SQLite database across test connections.
engine = create_engine(
    "sqlite+pysqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

session_factory = build_session_factory(engine)

# Create tables in the same shared test database.
Base.metadata.create_all(bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    with session_factory() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_create_task_returns_created_task() -> None:
    response = client.post(
        "/api/v1/tasks",
        json={
            "description": "Fix the failing unit test",
            "repository_url": "https://github.com/example/project",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["description"] == "Fix the failing unit test"
    assert data["repository_url"] == "https://github.com/example/project"
    assert data["status"] == "CREATED"
    assert data["id"]


def test_get_task_returns_saved_task() -> None:
    create_response = client.post(
        "/api/v1/tasks",
        json={"description": "Add input validation"},
    )
    assert create_response.status_code == 201

    task_id = create_response.json()["id"]
    response = client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200
    assert response.json()["id"] == task_id
    assert response.json()["description"] == "Add input validation"


def test_get_unknown_task_returns_404() -> None:
    response = client.get(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000001"
    )

    assert response.status_code == 404


def test_create_task_rejects_empty_description() -> None:
    response = client.post(
        "/api/v1/tasks",
        json={"description": ""},
    )

    assert response.status_code == 422
