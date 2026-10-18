import pytest

from app.services.repository_validator import (
    InvalidRepositoryURL,
    validate_github_repository_url,
)


def test_accepts_valid_github_repository_url() -> None:
    assert validate_github_repository_url(
        "https://github.com/owner/project"
    ) == "https://github.com/owner/project"


def test_normalizes_trailing_slash_and_git_suffix() -> None:
    assert validate_github_repository_url(
        "https://github.com/owner/project.git/"
    ) == "https://github.com/owner/project"


@pytest.mark.parametrize(
    "url",
    [
        "",
        " https://github.com/owner/project",
        "http://github.com/owner/project",
        "https://gitlab.com/owner/project",
        "https://user:pass@github.com/owner/project",
        "https://github.com:8443/owner/project",
        "https://github.com/owner/project?download=1",
        "https://github.com/owner",
        "https://github.com/owner/project/tree/main",
        "https://github.com/",
    ],
)
def test_rejects_invalid_repository_urls(url: str) -> None:
    with pytest.raises(InvalidRepositoryURL):
        validate_github_repository_url(url)