"""Document API routes."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.embeddings import delete_document, ingest_document, list_document_ids
from app.models.schemas import DocumentInfo

router = APIRouter(prefix="/documents", tags=["documents"])
_ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}


@router.post("/upload", response_model=DocumentInfo)
async def upload_document(file: UploadFile = File(...)) -> DocumentInfo:
    """Upload and ingest a document into the vector store."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, detail="Only PDF, TXT, and DOCX files are supported"
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir="/tmp") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    doc_id = f"{uuid.uuid4().hex}_{Path(file.filename or 'document').stem}"
    try:
        chunks = ingest_document(tmp_path, doc_id)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return DocumentInfo(doc_id=doc_id, chunks=chunks)


@router.get("", response_model=list[str])
async def get_documents() -> list[str]:
    """Return all ingested document IDs."""
    return list_document_ids()


@router.delete("/{doc_id}")
async def remove_document(doc_id: str) -> dict[str, str]:
    """Delete a document from the vector store."""
    delete_document(doc_id)
    return {"status": "deleted", "doc_id": doc_id}
