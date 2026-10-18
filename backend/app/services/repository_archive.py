
from __future__ import annotations

import os
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import httpx


GITHUB_ARCHIVE_HOST = "codeload.github.com"
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024  # 20 MiB
MAX_EXTRACTED_BYTES = 100 * 1024 * 1024  # 100 MiB
MAX_ARCHIVE_MEMBERS = 5_000
MAX_SINGLE_FILE_BYTES = 10 * 1024 * 1024  # 10 MiB
DOWNLOAD_TIMEOUT_SECONDS = 20.0


class RepositoryArchiveError(RuntimeError):
    """Base error for repository archive operations."""


class ArchiveDownloadError(RepositoryArchiveError):
    """Raised when an archive cannot be safely downloaded."""


class UnsafeArchiveError(RepositoryArchiveError):
    """Raised when an archive contains unsafe or unsupported entries."""


@dataclass(frozen=True)
class ExtractedRepository:
    root: Path
    file_count: int
    total_bytes: int


def build_archive_url(owner: str, repository: str, branch: str) -> str:
    """Build a codeload URL from individual, untrusted path segments."""
    for value, label in (
        (owner, "owner"),
        (repository, "repository"),
        (branch, "branch"),
    ):
        if not value or value in {".", ".."} or "/" in value or "\\" in value:
            raise ArchiveDownloadError(f"Invalid repository {label}.")

    return (
        f"https://{GITHUB_ARCHIVE_HOST}/"
        f"{quote(owner, safe='')}/{quote(repository, safe='')}/"
        f"tar.gz/refs/heads/{quote(branch, safe='')}"
    )


def _download_archive(
    url: str,
    destination: Path,
    *,
    client: httpx.Client | None = None,
) -> int:
    """Stream a trusted-host archive to disk with a hard size limit."""
    owns_client = client is None
    http_client = client or httpx.Client(
        timeout=DOWNLOAD_TIMEOUT_SECONDS,
        follow_redirects=False,
        trust_env=False,
    )

    total = 0

    try:
        with http_client.stream("GET", url) as response:
            if response.status_code != 200:
                raise ArchiveDownloadError(
                    f"Archive server returned HTTP {response.status_code}."
                )

            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    announced_size = int(content_length)
                except ValueError as exc:
                    raise ArchiveDownloadError(
                        "Archive server returned an invalid content length."
                    ) from exc

                if announced_size < 0 or announced_size > MAX_ARCHIVE_BYTES:
                    raise ArchiveDownloadError("Archive exceeds the download size limit.")

            with destination.open("wb") as output:
                for chunk in response.iter_bytes(chunk_size=64 * 1024):
                    total += len(chunk)

                    if total > MAX_ARCHIVE_BYTES:
                        raise ArchiveDownloadError(
                            "Archive exceeds the download size limit."
                        )

                    output.write(chunk)

        if total == 0:
            raise ArchiveDownloadError("Archive download was empty.")

        return total

    except httpx.TimeoutException as exc:
        raise ArchiveDownloadError("Archive download timed out.") from exc
    except httpx.RequestError as exc:
        raise ArchiveDownloadError("Could not download repository archive.") from exc
    finally:
        if owns_client:
            http_client.close()


def _safe_member_path(root: Path, name: str) -> Path:
    """Resolve a tar member path and reject traversal or absolute paths."""
    if not name or "\x00" in name or "\\" in name:
        raise UnsafeArchiveError("Archive contains an invalid path.")

    posix_path = PurePosixPath(name)

    if posix_path.is_absolute() or any(
        part in {"", ".", ".."} for part in posix_path.parts
    ):
        raise UnsafeArchiveError("Archive contains an unsafe path.")

    destination = root.joinpath(*posix_path.parts).resolve()
    resolved_root = root.resolve()

    if not destination.is_relative_to(resolved_root):
        raise UnsafeArchiveError("Archive path escapes the extraction directory.")

    return destination


def _extract_archive(archive_path: Path, destination: Path) -> ExtractedRepository:
    """Safely extract regular files and directories from a gzip tar archive."""
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()

    file_count = 0
    total_bytes = 0

    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            members = archive.getmembers()
            member_names: set[str] = set()

            for member in members:
                normalized_name = member.name.rstrip("/")
                if normalized_name in member_names:
                    raise UnsafeArchiveError("Archive contains duplicate paths.")
                member_names.add(normalized_name)

            if len(members) > MAX_ARCHIVE_MEMBERS:
                raise UnsafeArchiveError("Archive contains too many entries.")

            for member in members:
                target = _safe_member_path(root, member.name)

                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue

                # Do not extract symlinks, hardlinks, devices, or special files.
                if not member.isfile():
                    raise UnsafeArchiveError(
                        "Archive contains an unsupported entry type."
                    )

                if member.size < 0 or member.size > MAX_SINGLE_FILE_BYTES:
                    raise UnsafeArchiveError(
                        "Archive contains a file outside the allowed size limit."
                    )

                total_bytes += member.size
                if total_bytes > MAX_EXTRACTED_BYTES:
                    raise UnsafeArchiveError(
                        "Archive exceeds the extracted size limit."
                    )

                target.parent.mkdir(parents=True, exist_ok=True)

                # Exclusive creation prevents overwriting an existing file.
                with archive.extractfile(member) as source:
                    if source is None:
                        raise UnsafeArchiveError(
                            "Archive contains an unreadable file."
                        )

                    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                    file_descriptor = os.open(target, flags, 0o600)

                    with os.fdopen(file_descriptor, "wb") as output:
                        remaining = member.size

                        while remaining:
                            chunk = source.read(min(64 * 1024, remaining))
                            if not chunk:
                                raise UnsafeArchiveError(
                                    "Archive file ended unexpectedly."
                                )

                            output.write(chunk)
                            remaining -= len(chunk)

                file_count += 1

    except (tarfile.TarError, OSError) as exc:
        if isinstance(exc, UnsafeArchiveError):
            raise
        raise UnsafeArchiveError("Archive could not be safely extracted.") from exc

    return ExtractedRepository(
        root=root,
        file_count=file_count,
        total_bytes=total_bytes,
    )


def download_and_extract_repository(
    owner: str,
    repository: str,
    branch: str,
    *,
    client: httpx.Client | None = None,
) -> ExtractedRepository:
    """Download and extract an archive into a new temporary workspace."""
    url = build_archive_url(owner, repository, branch)

    # The host is fixed by build_archive_url; reject accidental URL changes.
    if not url.startswith(f"https://{GITHUB_ARCHIVE_HOST}/"):
        raise ArchiveDownloadError("Unexpected archive host.")

    workspace = Path(tempfile.mkdtemp(prefix="devpilot-repo-"))
    archive_path = workspace / "repository.tar.gz"
    source_root = workspace / "source"

    try:
        _download_archive(url, archive_path, client=client)
        result = _extract_archive(archive_path, source_root)
        archive_path.unlink(missing_ok=True)
        return result
    except Exception:
        # Clean up partial downloads and extracted files after failures.
        import shutil

        shutil.rmtree(workspace, ignore_errors=True)
        raise
