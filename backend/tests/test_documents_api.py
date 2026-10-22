"""Tests for document API endpoints."""

from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import documents as documents_module
from app.core.embeddings import IngestResult
from app.main import app

client = TestClient(app)


def _upload(content: bytes = b"hello world", name: str = "notes.txt"):
    return client.post(
        "/api/documents/upload",
        files={"file": (name, BytesIO(content), "text/plain")},
    )


def test_upload_success(monkeypatch) -> None:
    """A valid upload returns the document summary."""
    monkeypatch.setattr(
        documents_module,
        "ingest_document",
        lambda path, doc_id, filename: IngestResult(doc_id=doc_id, chunks=4),
    )

    response = _upload()

    assert response.status_code == 200
    body = response.json()
    assert body["chunks"] == 4
    assert body["filename"] == "notes.txt"
    assert body["duplicate"] is False
    assert body["doc_id"].endswith("_notes")


def test_upload_duplicate_is_reported(monkeypatch) -> None:
    """Re-uploading identical content returns the original document."""
    monkeypatch.setattr(
        documents_module,
        "ingest_document",
        lambda path, doc_id, filename: IngestResult(
            doc_id="original-id", chunks=0, duplicate=True
        ),
    )

    response = _upload()

    assert response.status_code == 200
    assert response.json() == {
        "doc_id": "original-id",
        "filename": "notes.txt",
        "chunks": 0,
        "duplicate": True,
    }


def test_upload_without_text_returns_400(monkeypatch) -> None:
    """A file that yields no text is a client error, not a silent success."""
    monkeypatch.setattr(
        documents_module,
        "ingest_document",
        lambda path, doc_id, filename: IngestResult(doc_id=doc_id, chunks=0),
    )

    response = _upload(b"   ", "blank.txt")

    assert response.status_code == 400
    assert "no extractable text" in response.json()["detail"].lower()


def test_upload_oversized_file_returns_413(monkeypatch) -> None:
    """The size limit is enforced while streaming the upload."""
    monkeypatch.setattr(
        documents_module,
        "get_settings",
        lambda: SimpleNamespace(max_upload_bytes=1024),
    )

    response = _upload(b"x" * 4096, "big.txt")

    assert response.status_code == 413
    assert "too large" in response.json()["detail"].lower()


def test_unsupported_extension_returns_400() -> None:
    """Only PDF, TXT and DOCX are accepted."""
    response = _upload(b"binary", "malware.exe")

    assert response.status_code == 400


def test_delete_nonexistent_document_returns_404(monkeypatch) -> None:
    """DELETE /api/documents/{doc_id} should return 404 for unknown doc_id."""
    monkeypatch.setattr(documents_module, "list_document_ids", lambda: [])

    response = client.delete("/api/documents/nonexistent-id")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_delete_existing_document(monkeypatch) -> None:
    """Deleting a known document succeeds and calls through."""
    deleted: list[str] = []
    monkeypatch.setattr(documents_module, "list_document_ids", lambda: ["doc-1"])
    monkeypatch.setattr(documents_module, "delete_document", deleted.append)

    response = client.delete("/api/documents/doc-1")

    assert response.status_code == 200
    assert response.json() == {"status": "deleted", "doc_id": "doc-1"}
    assert deleted == ["doc-1"]


def test_list_documents_returns_summaries(monkeypatch) -> None:
    """The listing includes filenames and chunk counts."""
    monkeypatch.setattr(
        documents_module,
        "list_documents",
        lambda: [{"doc_id": "a", "filename": "a.pdf", "chunks": 3}],
    )

    response = client.get("/api/documents")

    assert response.status_code == 200
    assert response.json() == [{"doc_id": "a", "filename": "a.pdf", "chunks": 3}]


def test_doc_id_stem_is_sanitised(monkeypatch) -> None:
    """Hostile filenames must not leak into the document id."""
    captured: dict = {}

    def fake_ingest(path, doc_id, filename):
        captured["doc_id"] = doc_id
        return IngestResult(doc_id=doc_id, chunks=1)

    monkeypatch.setattr(documents_module, "ingest_document", fake_ingest)

    _upload(b"data", "../../etc/passwd.txt")

    assert ".." not in captured["doc_id"]
    assert "/" not in captured["doc_id"]
    assert captured["doc_id"].endswith("_passwd")
