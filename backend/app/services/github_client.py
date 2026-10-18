
from dataclasses import dataclass
from urllib.parse import quote

import httpx

from app.services.repository_validator import (
    InvalidRepositoryURL,
    validate_github_repository_url,
)


GITHUB_API_BASE = "https://api.github.com"
REQUEST_TIMEOUT_SECONDS = 8.0


class GitHubClientError(RuntimeError):
    """Base error for GitHub metadata requests."""


class RepositoryNotFoundError(GitHubClientError):
    """Raised when the repository does not exist or is not public."""


class GitHubRateLimitError(GitHubClientError):
    """Raised when GitHub rate limits the request."""


class GitHubServiceError(GitHubClientError):
    """Raised when GitHub cannot provide valid metadata."""


@dataclass(frozen=True)
class RepositoryMetadata:
    owner: str
    name: str
    full_name: str
    description: str | None
    default_branch: str
    html_url: str
    is_private: bool


def _validate_metadata(payload: object) -> RepositoryMetadata:
    """Parse only the metadata fields DevPilot needs."""
    if not isinstance(payload, dict):
        raise GitHubServiceError("GitHub returned an invalid response.")

    owner_data = payload.get("owner")
    if not isinstance(owner_data, dict):
        raise GitHubServiceError("GitHub response is missing owner metadata.")

    owner = owner_data.get("login")
    name = payload.get("name")
    full_name = payload.get("full_name")
    default_branch = payload.get("default_branch")
    html_url = payload.get("html_url")
    description = payload.get("description")
    is_private = payload.get("private")

    if not all(
        isinstance(value, str) and value
        for value in (owner, name, full_name, default_branch, html_url)
    ):
        raise GitHubServiceError("GitHub response contains invalid metadata.")

    if description is not None and not isinstance(description, str):
        raise GitHubServiceError("GitHub response contains an invalid description.")

    if not isinstance(is_private, bool):
        raise GitHubServiceError("GitHub response contains invalid visibility metadata.")

    if is_private:
        raise RepositoryNotFoundError(
            "The repository is private or unavailable publicly."
        )

    # Only accept GitHub's canonical HTTPS repository URL.
    expected_url = f"https://github.com/{owner}/{name}"
    if html_url.rstrip("/") != expected_url:
        raise GitHubServiceError("GitHub returned an unexpected repository URL.")

    return RepositoryMetadata(
        owner=owner,
        name=name,
        full_name=full_name,
        description=description,
        default_branch=default_branch,
        html_url=expected_url,
        is_private=False,
    )


def get_repository_metadata(
    repository_url: str,
    *,
    client: httpx.Client | None = None,
) -> RepositoryMetadata:
    """Fetch metadata for a public GitHub repository without redirects."""
    normalized_url = validate_github_repository_url(repository_url)
    path = normalized_url.removeprefix("https://github.com/")

    owner, repository = path.split("/", maxsplit=1)

    # Encode each path segment independently to avoid path manipulation.
    api_path = (
        f"{quote(owner, safe='')}/{quote(repository, safe='')}"
    )
    api_url = f"{GITHUB_API_BASE}/repos/{api_path}"

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "DevPilot-AI",
    }

    owns_client = client is None
    http_client = client or httpx.Client(
        timeout=REQUEST_TIMEOUT_SECONDS,
        follow_redirects=False,
        trust_env=False,
    )

    try:
        response = http_client.get(api_url, headers=headers)

        if 300 <= response.status_code < 400:
            raise GitHubServiceError(
                "GitHub returned a redirect; redirects are not followed."
            )

        if response.status_code == 404:
            raise RepositoryNotFoundError(
                "Repository not found or not publicly accessible."
            )

        if response.status_code == 403 and (
            "rate limit" in response.text.lower()
            or response.headers.get("X-RateLimit-Remaining") == "0"
        ):
            raise GitHubRateLimitError(
                "GitHub API rate limit reached. Try again later."
            )

        if response.status_code != 200:
            raise GitHubServiceError(
                f"GitHub API request failed with status {response.status_code}."
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise GitHubServiceError(
                "GitHub returned invalid JSON."
            ) from exc

        return _validate_metadata(payload)

    except httpx.TimeoutException as exc:
        raise GitHubServiceError("GitHub request timed out.") from exc
    except httpx.RequestError as exc:
        raise GitHubServiceError("Could not reach GitHub.") from exc
    finally:
        if owns_client:
            http_client.close()
