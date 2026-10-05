"""Tests for nysc_safety.download. No network requests are made."""

from pathlib import Path

import pytest

from nysc_safety import download, sources


def test_documents_are_in_source_log() -> None:
    """Every document to download has a row in docs/sources.md."""
    logged = sources.logged_ids()
    assert all(doc.source_id in logged for doc in download.DOCUMENTS)


def test_filenames_are_unique_and_prefixed() -> None:
    """File names are unique and start with the source ID."""
    names = [doc.filename for doc in download.DOCUMENTS]
    assert len(names) == len(set(names))
    assert all(doc.filename.startswith(doc.source_id + "_") for doc in download.DOCUMENTS)


def test_existing_file_is_not_overwritten(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An existing file is returned unchanged and no request is made."""
    doc = download.DOCUMENTS[0]
    existing = tmp_path / doc.filename
    existing.write_bytes(b"%PDF-existing")

    def fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("a request was made")

    monkeypatch.setattr(download.requests, "get", fail)
    assert download.download(doc, tmp_path) == existing
    assert existing.read_bytes() == b"%PDF-existing"


class FakeResponse:
    """Minimal stand-in for a streamed requests response."""

    def __init__(self, body: bytes) -> None:
        self.body = body
        self.headers = {"content-length": str(len(body))}

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int) -> list[bytes]:
        return [self.body[i : i + chunk_size] for i in range(0, len(self.body), chunk_size)]


def test_download_writes_complete_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A PDF response is saved under the final name and no .part file remains."""
    doc = download.DOCUMENTS[0]
    monkeypatch.setattr(download.requests, "get", lambda *a, **k: FakeResponse(b"%PDF-1.4 body"))
    path = download.download(doc, tmp_path)
    assert path.read_bytes() == b"%PDF-1.4 body"
    assert not list(tmp_path.glob("*.part"))


def test_non_pdf_response_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An HTML error page is rejected and leaves no file behind."""
    doc = download.DOCUMENTS[0]
    monkeypatch.setattr(download.requests, "get", lambda *a, **k: FakeResponse(b"<html>error</html>"))
    with pytest.raises(ValueError):
        download.download(doc, tmp_path)
    assert list(tmp_path.iterdir()) == []
