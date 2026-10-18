
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    description: str = Field(min_length=1, max_length=10_000)
    repository_url: str | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    description: str
    repository_url: str | None
    status: str
    created_at: datetime
    updated_at: datetime
