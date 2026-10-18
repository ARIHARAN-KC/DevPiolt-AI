
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import TaskCreate, TaskResponse
from app.db.models import Task
from app.db.session import get_db
from app.services.github_client import (
    GitHubRateLimitError,
    GitHubServiceError,
    RepositoryNotFoundError,
    get_repository_metadata,
)
from app.services.repository_validator import InvalidRepositoryURL

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
) -> Task:
    """Validate an optional public repository before saving a task."""
    repository_url = payload.repository_url

    if repository_url is not None:
        try:
            metadata = get_repository_metadata(repository_url)
            repository_url = metadata.html_url

        except InvalidRepositoryURL as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        except RepositoryNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repository not found or not publicly accessible.",
            ) from exc

        except GitHubRateLimitError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GitHub rate limit reached. Please try again later.",
            ) from exc

        except GitHubServiceError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not verify the GitHub repository.",
            ) from exc

    task = Task(
        description=payload.description,
        repository_url=repository_url,
        status="CREATED",
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return task


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
) -> Task:
    """Retrieve a task by its UUID."""
    task = db.get(Task, task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    return task
