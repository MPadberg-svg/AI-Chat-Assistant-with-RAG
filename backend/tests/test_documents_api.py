"""Tests for document API endpoints."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_delete_nonexistent_document_returns_404() -> None:
    """DELETE /api/documents/{doc_id} should return 404 for unknown doc_id."""
    with patch(
        "app.api.documents.list_document_ids", return_value=[]
    ):
        response = client.delete("/api/documents/nonexistent-id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_upload_oversized_file_returns_413() -> None:
    """POST /api/documents/upload should return 413 for files exceeding size limit."""
    from io import BytesIO

    oversized_content = b"x" * (21 * 1024 * 1024)  # 21 MB
    with patch("app.api.documents.get_settings") as mock_settings:
        mock_settings.return_value.max_upload_bytes = 20 * 1024 * 1024
        response = client.post(
            "/api/documents/upload",
            files={"file": ("big.txt", BytesIO(oversized_content), "text/plain")},
        )
    assert response.status_code == 413
