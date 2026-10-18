
import io
import tarfile
from pathlib import Path

import httpx
import pytest

from app.services.repository_archive import (
    ArchiveDownloadError,
    MAX_ARCHIVE_BYTES,
    UnsafeArchiveError,
    _download_archive,
    _extract_archive,
    build_archive_url,
)


def make_tar(entries: list[tuple[str, bytes, str]]) -> bytes:
    """Build an in-memory gzip tar for security tests."""
    buffer = io.BytesIO()

    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, content, entry_type in entries:
            info = tarfile.TarInfo(name=name)

            if entry_type == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = "../../outside.txt"
                archive.addfile(info)
            else:
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))

    return buffer.getvalue()


def test_builds_expected_archive_url() -> None:
    assert build_archive_url("owner", "project", "main") == (
        "https://codeload.github.com/owner/project/"
        "tar.gz/refs/heads/main"
    )


@pytest.mark.parametrize(
    ("owner", "repository", "branch"),
    [
        ("..", "project", "main"),
        ("owner/name", "project", "main"),
        ("owner", "../project", "main"),
        ("owner", "project", "feature/branch"),
        ("owner", "project", ".."),
    ],
)
def test_rejects_unsafe_url_segments(
    owner: str,
    repository: str,
    branch: str,
) -> None:
    with pytest.raises(ArchiveDownloadError):
        build_archive_url(owner, repository, branch)


def test_download_rejects_redirect(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"Location": "https://example.com/archive"},
            request=request,
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    try:
        with pytest.raises(ArchiveDownloadError, match="HTTP 302"):
            _download_archive(
                "https://codeload.github.com/owner/project/archive.tar.gz",
                tmp_path / "archive.tar.gz",
                client=client,
            )
    finally:
        client.close()


def test_download_rejects_oversized_content_length(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Length": str(MAX_ARCHIVE_BYTES + 1)},
            content=b"x",
            request=request,
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    try:
        with pytest.raises(ArchiveDownloadError, match="size limit"):
            _download_archive(
                "https://codeload.github.com/owner/project/archive.tar.gz",
                tmp_path / "archive.tar.gz",
                client=client,
            )
    finally:
        client.close()


def test_extracts_regular_file(tmp_path: Path) -> None:
    archive_bytes = make_tar([("project/README.md", b"hello", "file")])
    archive_path = tmp_path / "valid.tar.gz"
    archive_path.write_bytes(archive_bytes)

    result = _extract_archive(archive_path, tmp_path / "output")

    assert result.file_count == 1
    assert (result.root / "project" / "README.md").read_text() == "hello"


@pytest.mark.parametrize(
    "unsafe_name",
    [
        "../outside.txt",
        "/absolute.txt",
        "project/../../outside.txt",
        r"project\..\outside.txt",
    ],
)
def test_rejects_unsafe_archive_paths(
    tmp_path: Path,
    unsafe_name: str,
) -> None:
    archive_bytes = make_tar([(unsafe_name, b"bad", "file")])
    archive_path = tmp_path / "unsafe.tar.gz"
    archive_path.write_bytes(archive_bytes)

    with pytest.raises(UnsafeArchiveError):
        _extract_archive(archive_path, tmp_path / "output")

    assert not (tmp_path / "outside.txt").exists()


def test_rejects_symbolic_links(tmp_path: Path) -> None:
    archive_bytes = make_tar([("project/link", b"", "symlink")])
    archive_path = tmp_path / "link.tar.gz"
    archive_path.write_bytes(archive_bytes)

    with pytest.raises(UnsafeArchiveError, match="unsupported entry type"):
        _extract_archive(archive_path, tmp_path / "output")

def test_rejects_duplicate_archive_paths(tmp_path: Path) -> None:
    archive_bytes = make_tar(
        [
            ("project/README.md", b"first", "file"),
            ("project/README.md", b"second", "file"),
        ]
    )
    archive_path = tmp_path / "duplicate.tar.gz"
    archive_path.write_bytes(archive_bytes)

    with pytest.raises(UnsafeArchiveError, match="duplicate paths"):
        _extract_archive(archive_path, tmp_path / "output")