from urllib.parse import urlsplit


class InvalidRepositoryURL(ValueError):
    """Raised when a repository URL is invalid or unsupported."""


def validate_github_repository_url(url: str) -> str:
    """Validate and normalize a public GitHub HTTPS repository URL."""
    if not url or url != url.strip():
        raise InvalidRepositoryURL("Repository URL must not be empty or padded.")

    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise InvalidRepositoryURL("Malformed repository URL.") from exc

    if parsed.scheme != "https":
        raise InvalidRepositoryURL("Only HTTPS repository URLs are supported.")

    if parsed.hostname != "github.com":
        raise InvalidRepositoryURL("Only github.com repository URLs are supported.")

    if parsed.username or parsed.password:
        raise InvalidRepositoryURL("Credentials must not appear in repository URLs.")

    if port not in (None, 443):
        raise InvalidRepositoryURL("Custom ports are not supported.")

    if parsed.query or parsed.fragment:
        raise InvalidRepositoryURL("Query strings and fragments are not supported.")

    parts = parsed.path.strip("/").split("/")

    if len(parts) != 2 or not all(parts):
        raise InvalidRepositoryURL(
            "Use the format https://github.com/owner/repository."
        )

    owner, repository = parts

    if owner in {".", ".."} or repository in {".", ".."}:
        raise InvalidRepositoryURL("Invalid repository path.")

    if repository.endswith(".git"):
        repository = repository[:-4]

    if not repository:
        raise InvalidRepositoryURL("Repository name is missing.")

    return f"https://github.com/{owner}/{repository}"