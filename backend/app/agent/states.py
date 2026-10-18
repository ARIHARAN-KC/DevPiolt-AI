
from enum import StrEnum


class TaskStatus(StrEnum):
    """Supported lifecycle states for a coding-agent task."""

    CREATED = "CREATED"
    REPOSITORY_READY = "REPOSITORY_READY"
    ANALYZING = "ANALYZING"
    PLAN_READY = "PLAN_READY"
    PATCH_READY = "PATCH_READY"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    VALIDATING = "VALIDATING"
    TESTING = "TESTING"
    REPAIRING = "REPAIRING"
    SUCCEEDED = "SUCCEEDED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.CREATED: {TaskStatus.REPOSITORY_READY, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.REPOSITORY_READY: {TaskStatus.ANALYZING, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.ANALYZING: {TaskStatus.PLAN_READY, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.PLAN_READY: {TaskStatus.PATCH_READY, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.PATCH_READY: {TaskStatus.AWAITING_APPROVAL, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.AWAITING_APPROVAL: {TaskStatus.VALIDATING, TaskStatus.REJECTED, TaskStatus.CANCELLED},
    TaskStatus.VALIDATING: {TaskStatus.TESTING, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.TESTING: {TaskStatus.SUCCEEDED, TaskStatus.REPAIRING, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.REPAIRING: {TaskStatus.PATCH_READY, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.SUCCEEDED: set(),
    TaskStatus.REJECTED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
}


class InvalidTaskTransition(ValueError):
    """Raised when a task attempts an unsupported state transition."""


def transition_task(
    current: TaskStatus,
    target: TaskStatus,
) -> TaskStatus:
    """Validate a transition and return the new status."""
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTaskTransition(
            f"Cannot transition task from {current.value} to {target.value}."
        )

    return target
