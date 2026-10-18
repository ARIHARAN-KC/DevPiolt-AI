
import httpx
import pytest

from app.services.github_client import (
    GitHubServiceError,
    RepositoryNotFoundError,
    get_repository_metadata,
)


def make_response(
    status_code: int,
    payload: object | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    request = httpx.Request(
        "GET",
        "https://api.github.com/repos/owner/project",
    )
    return httpx.Response(
        status_code,
        json=payload if payload is not None else {},
        headers=headers,
        request=request,
    )


def make_client(response: httpx.Response) -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(lambda request: response),
        follow_redirects=False,
    )


def valid_payload() -> dict:
    return {
        "owner": {"login": "owner"},
        "name": "project",
        "full_name": "owner/project",
        "description": "A sample project",
        "default_branch": "main",
        "html_url": "https://github.com/owner/project",
        "private": False,
    }


def test_fetches_public_repository_metadata() -> None:
    client = make_client(make_response(200, valid_payload()))

    result = get_repository_metadata(
        "https://github.com/owner/project",
        client=client,
    )

    assert result.full_name == "owner/project"
    assert result.default_branch == "main"
    assert result.is_private is False
    client.close()


def test_404_returns_repository_not_found() -> None:
    client = make_client(make_response(404))

    try:
        with pytest.raises(RepositoryNotFoundError):
            get_repository_metadata(
                "https://github.com/owner/missing",
                client=client,
            )
    finally:
        client.close()


def test_redirect_is_rejected() -> None:
    client = make_client(
        make_response(
            302,
            headers={"Location": "https://example.com/"},
        )
    )

    try:
        with pytest.raises(GitHubServiceError, match="redirect"):
            get_repository_metadata(
                "https://github.com/owner/project",
                client=client,
            )
    finally:
        client.close()


def test_private_repository_is_rejected() -> None:
    payload = valid_payload()
    payload["private"] = True
    client = make_client(make_response(200, payload))

    try:
        with pytest.raises(RepositoryNotFoundError):
            get_repository_metadata(
                "https://github.com/owner/project",
                client=client,
            )
    finally:
        client.close()


def test_unexpected_html_url_is_rejected() -> None:
    payload = valid_payload()
    payload["html_url"] = "https://example.com/owner/project"
    client = make_client(make_response(200, payload))

    try:
        with pytest.raises(GitHubServiceError, match="unexpected repository URL"):
            get_repository_metadata(
                "https://github.com/owner/project",
                client=client,
            )
    finally:
        client.close()
