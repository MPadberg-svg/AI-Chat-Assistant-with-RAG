"""ChromaDB and embedding utilities."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import chromadb
from docx import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from pypdf import PdfReader

from app.core.config import get_settings

_COLLECTION_NAME = "documents"

_client: chromadb.PersistentClient | None = None
_collection: Any | None = None


def get_chroma_client() -> chromadb.PersistentClient:
    """Return a cached ChromaDB persistent client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return _client


def get_collection() -> Any:
    """Return the shared document collection."""
    global _collection
    if _collection is None:
        _collection = get_chroma_client().get_or_create_collection(
            name=_COLLECTION_NAME
        )
    return _collection


def _get_embeddings_model() -> OpenAIEmbeddings:
    """Return the embedding model instance."""
    settings = get_settings()
    return OpenAIEmbeddings(
        model="text-embedding-3-small", api_key=settings.openai_api_key
    )


def _extract_segments(file_path: str) -> list[tuple[str, int]]:
    """Extract text segments and page numbers from a file path."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        reader = PdfReader(file_path)
        return [
            ((page.extract_text() or ""), index + 1)
            for index, page in enumerate(reader.pages)
        ]

    if suffix == ".docx":
        doc = Document(file_path)
        text = "\n".join(paragraph.text for paragraph in doc.paragraphs).strip()
        return [(text, 1)]

    text = path.read_text(encoding="utf-8", errors="ignore")
    return [(text, 1)]


def ingest_document(file_path: str, doc_id: str) -> int:
    """Split, embed, and store a document. Returns the number of chunks created."""
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    chunks: list[str] = []
    metadatas: list[dict[str, Any]] = []
    ids: list[str] = []

    for segment, page in _extract_segments(file_path):
        if not segment.strip():
            continue
        split_chunks = splitter.split_text(segment)
        for index, chunk in enumerate(split_chunks):
            chunks.append(chunk)
            metadatas.append({"doc_id": doc_id, "page": page})
            ids.append(f"{doc_id}:{page}:{index}")

    if not chunks:
        return 0

    embeddings = _get_embeddings_model().embed_documents(chunks)
    get_collection().add(
        ids=ids, documents=chunks, metadatas=metadatas, embeddings=embeddings
    )
    return len(chunks)


def list_document_ids() -> list[str]:
    """List unique ingested document IDs from ChromaDB."""
    payload = get_collection().get(include=["metadatas"])
    metadatas = payload.get("metadatas", [])
    ids = {item.get("doc_id") for item in metadatas if item and item.get("doc_id")}
    return sorted(ids)


def delete_document(doc_id: str) -> None:
    """Delete all chunks for a given document ID."""
    collection = get_collection()
    collection.delete(where={"doc_id": doc_id})

    persist_dir = Path(get_settings().chroma_persist_dir)
    os.makedirs(persist_dir, exist_ok=True)
