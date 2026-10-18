
import pytest

from app.agent.states import (
    InvalidTaskTransition,
    TaskStatus,
    transition_task,
)


def test_valid_transition_is_allowed() -> None:
    result = transition_task(
        TaskStatus.CREATED,
        TaskStatus.REPOSITORY_READY,
    )

    assert result == TaskStatus.REPOSITORY_READY


def test_patch_cannot_skip_approval() -> None:
    with pytest.raises(InvalidTaskTransition):
        transition_task(
            TaskStatus.PATCH_READY,
            TaskStatus.TESTING,
        )


def test_approved_patch_can_be_validated() -> None:
    result = transition_task(
        TaskStatus.AWAITING_APPROVAL,
        TaskStatus.VALIDATING,
    )

    assert result == TaskStatus.VALIDATING


def test_terminal_state_cannot_restart() -> None:
    with pytest.raises(InvalidTaskTransition):
        transition_task(
            TaskStatus.SUCCEEDED,
            TaskStatus.ANALYZING,
        )


def test_failed_test_can_enter_repairing() -> None:
    result = transition_task(
        TaskStatus.TESTING,
        TaskStatus.REPAIRING,
    )

    assert result == TaskStatus.REPAIRING
