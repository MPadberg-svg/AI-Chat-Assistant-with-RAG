"""Document API routes."""

from __future__ import annotations

import re
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.embeddings import (
    delete_document,
    ingest_document,
    list_document_ids,
    list_documents,
)
from app.models.schemas import DocumentInfo, DocumentSummary

router = APIRouter(prefix="/documents", tags=["documents"])

_ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}
_READ_CHUNK = 1024 * 1024


def _safe_stem(filename: str | None) -> str:
    """Build a filesystem-safe, length-limited name stem from an upload name."""
    stem = Path(filename or "document").stem
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", stem).strip("-")
    return (cleaned or "document")[:60]


async def _persist_upload(file: UploadFile, suffix: str, max_bytes: int) -> Path:
    """Stream an upload to a temporary file, enforcing the size limit as it goes.

    Reading the whole body first (the previous behaviour) allowed unbounded
    memory use per concurrent request; the limit is now applied while copying.
    """
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    path = Path(temp.name)
    try:
        with temp:
            total = 0
            while True:
                block = await file.read(_READ_CHUNK)
                if not block:
                    break
                total += len(block)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "File too large. Maximum size is "
                            f"{max_bytes // (1024 * 1024)} MB"
                        ),
                    )
                temp.write(block)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path


@router.post("/upload", response_model=DocumentInfo)
async def upload_document(file: UploadFile = File(...)) -> DocumentInfo:
    """Upload and ingest a document into the vector store."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, detail="Only PDF, TXT, and DOCX files are supported"
        )

    settings = get_settings()
    temp_path = await _persist_upload(file, suffix, settings.max_upload_bytes)
    doc_id = f"{uuid.uuid4().hex[:12]}_{_safe_stem(file.filename)}"

    try:
        result = await run_in_threadpool(
            ingest_document, str(temp_path), doc_id, file.filename
        )
    finally:
        temp_path.unlink(missing_ok=True)

    if result.chunks == 0 and not result.duplicate:
        raise HTTPException(
            status_code=400,
            detail="No extractable text was found in this document",
        )

    return DocumentInfo(
        doc_id=result.doc_id,
        filename=file.filename or result.doc_id,
        chunks=result.chunks,
        duplicate=result.duplicate,
    )


@router.get("", response_model=list[DocumentSummary])
async def get_documents() -> list[DocumentSummary]:
    """Return one summary per ingested document."""
    documents = await run_in_threadpool(list_documents)
    return [DocumentSummary(**document) for document in documents]


@router.delete("/{doc_id}")
async def remove_document(doc_id: str) -> dict[str, str]:
    """Delete a document from the vector store."""
    existing = await run_in_threadpool(list_document_ids)
    if doc_id not in existing:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")
    await run_in_threadpool(delete_document, doc_id)
    return {"status": "deleted", "doc_id": doc_id}
