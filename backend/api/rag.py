"""RAG API - Document ingestion and search"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
import logging
import aiofiles
import os
from datetime import datetime

from db.database import get_db_session
from db.models import Neuron as NeuronModel, Document, User, PrivacyTier
from api.auth import get_current_user
from core.neuron.neuron_manager import get_neuron_manager
from core.security.audit import log_audit_event
from core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


class DocumentUpload(BaseModel):
    neuron_id: str
    title: str
    content: str
    metadata: Optional[dict] = None


class DocumentResponse(BaseModel):
    id: str
    neuron_id: str
    title: str
    content: str
    source: Optional[str]
    chunk_count: int
    created_at: str

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    doc_id: str
    text: str
    score: float
    metadata: dict


class SearchRequest(BaseModel):
    query: str
    top_k: int = 3


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks.

    Args:
        text: Text to chunk
        chunk_size: Maximum chunk size in characters
        overlap: Overlap between chunks

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence end within last 100 chars
            period_pos = text.rfind('.', end - 100, end)
            if period_pos > start:
                end = period_pos + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start with overlap
        start = end - overlap

    logger.debug(f"Chunked text into {len(chunks)} chunks")
    return chunks


async def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from PDF file.

    Args:
        file_path: Path to PDF file

    Returns:
        Extracted text
    """
    try:
        # Try using PyPDF2 (lightweight)
        import PyPDF2

        text = ""
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n\n"

        return text.strip()

    except ImportError:
        logger.warning("PyPDF2 not installed, cannot extract PDF text")
        raise HTTPException(
            status_code=400,
            detail="PDF processing not available. Install PyPDF2."
        )
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to extract PDF: {str(e)}")


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    doc: DocumentUpload,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Upload document to Neuron's Axon (RAG memory).

    This endpoint:
    1. Verifies neuron ownership
    2. Chunks document intelligently
    3. Stores in Axon (FAISS vector store)
    4. Saves Document model to database
    """
    # 1. Verify neuron ownership
    result = await db.execute(
        select(NeuronModel).where(
            NeuronModel.id == doc.neuron_id,
            NeuronModel.owner_id == user.id
        )
    )
    neuron_model = result.scalar_one_or_none()

    if not neuron_model:
        raise HTTPException(status_code=404, detail="Neuron not found")

    # 2. Chunk document
    chunks = chunk_text(doc.content, chunk_size=512, overlap=50)

    # 3. Get/create Neuron instance with Axon
    manager = await get_neuron_manager()
    neuron = await manager.get_neuron(doc.neuron_id)

    if not neuron:
        neuron = await manager.add_neuron(doc.neuron_id, neuron_model.config)

    # Ensure Axon is enabled
    if not neuron.axon:
        raise HTTPException(
            status_code=400,
            detail="Axon (RAG) is not enabled for this Neuron"
        )

    # 4. Create document record
    document = Document(
        neuron_id=doc.neuron_id,
        title=doc.title,
        content=doc.content,
        source="api_upload",
        metadata=doc.metadata or {},
        privacy_tier=neuron_model.privacy_tier,
        embedding_model=settings.DEFAULT_EMBEDDING_MODEL,
        chunk_count=len(chunks)
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    # 5. Add chunks to Axon
    chunk_docs = [
        {
            "id": f"{document.id}_chunk_{i}",
            "text": chunk,
            "metadata": {
                "document_id": document.id,
                "title": doc.title,
                "chunk_index": i,
                "total_chunks": len(chunks),
                **(doc.metadata or {})
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        for i, chunk in enumerate(chunks)
    ]

    await neuron.axon.add_documents(chunk_docs)

    # 6. Audit log
    await log_audit_event(
        db=db,
        event_type="rag",
        action="upload_document",
        user_id=user.id,
        neuron_id=doc.neuron_id,
        result="success",
        details={
            "document_id": document.id,
            "chunk_count": len(chunks)
        }
    )

    logger.info(f"Document uploaded: {doc.title} ({len(chunks)} chunks)")

    return DocumentResponse(
        id=document.id,
        neuron_id=document.neuron_id,
        title=document.title,
        content=document.content,
        source=document.source,
        chunk_count=document.chunk_count,
        created_at=document.created_at.isoformat()
    )


@router.post("/upload-file", response_model=DocumentResponse)
async def upload_file(
    neuron_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Upload file (text, PDF) to Neuron's Axon.

    Supported formats:
    - .txt (plain text)
    - .pdf (PDF documents)
    - .md (Markdown)
    """
    # 1. Verify neuron ownership
    result = await db.execute(
        select(NeuronModel).where(
            NeuronModel.id == neuron_id,
            NeuronModel.owner_id == user.id
        )
    )
    neuron_model = result.scalar_one_or_none()

    if not neuron_model:
        raise HTTPException(status_code=404, detail="Neuron not found")

    # 2. Save file temporarily
    upload_dir = os.path.join(settings.STORAGE_PATH, "uploads", neuron_id)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, file.filename)

    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    logger.info(f"File uploaded: {file.filename}")

    # 3. Extract text based on file type
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext == ".pdf":
        text = await extract_text_from_pdf(file_path)
    elif file_ext in [".txt", ".md"]:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            text = await f.read()
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Use .txt, .md, or .pdf"
        )

    # 4. Use upload_document logic
    doc_upload = DocumentUpload(
        neuron_id=neuron_id,
        title=file.filename,
        content=text,
        metadata={
            "source_type": "file_upload",
            "filename": file.filename,
            "file_size": len(content),
            "file_type": file_ext
        }
    )

    return await upload_document(doc_upload, user, db)


@router.post("/search/{neuron_id}", response_model=List[SearchResult])
async def search_documents(
    neuron_id: str,
    search: SearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Search documents in Neuron's Axon using semantic search.

    Returns:
        List of relevant document chunks with scores
    """
    # 1. Verify neuron ownership
    result = await db.execute(
        select(NeuronModel).where(
            NeuronModel.id == neuron_id,
            NeuronModel.owner_id == user.id
        )
    )
    neuron_model = result.scalar_one_or_none()

    if not neuron_model:
        raise HTTPException(status_code=404, detail="Neuron not found")

    # 2. Get Neuron with Axon
    manager = await get_neuron_manager()
    neuron = await manager.get_neuron(neuron_id)

    if not neuron:
        neuron = await manager.add_neuron(neuron_id, neuron_model.config)

    if not neuron.axon:
        raise HTTPException(
            status_code=400,
            detail="Axon (RAG) is not enabled for this Neuron"
        )

    # 3. Search
    results = await neuron.axon.search(search.query, top_k=search.top_k)

    # 4. Audit log
    await log_audit_event(
        db=db,
        event_type="rag",
        action="search",
        user_id=user.id,
        neuron_id=neuron_id,
        result="success",
        details={
            "query": search.query,
            "results_count": len(results)
        }
    )

    return [
        SearchResult(
            doc_id=r.get("id", "unknown"),
            text=r.get("text", ""),
            score=r.get("score", 0.0),
            metadata=r.get("metadata", {})
        )
        for r in results
    ]


@router.get("/{neuron_id}/documents", response_model=List[DocumentResponse])
async def list_documents(
    neuron_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List all documents for a neuron"""
    # Verify neuron ownership
    result = await db.execute(
        select(NeuronModel).where(
            NeuronModel.id == neuron_id,
            NeuronModel.owner_id == user.id
        )
    )
    neuron = result.scalar_one_or_none()

    if not neuron:
        raise HTTPException(status_code=404, detail="Neuron not found")

    # Get documents
    docs_result = await db.execute(
        select(Document).where(
            Document.neuron_id == neuron_id
        ).order_by(Document.created_at.desc())
    )
    documents = docs_result.scalars().all()

    return [
        DocumentResponse(
            id=d.id,
            neuron_id=d.neuron_id,
            title=d.title,
            content=d.content[:200] + "..." if len(d.content) > 200 else d.content,
            source=d.source,
            chunk_count=d.chunk_count,
            created_at=d.created_at.isoformat()
        )
        for d in documents
    ]


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete document from Neuron's Axon"""
    # Get document
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = doc_result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Verify neuron ownership
    neuron_result = await db.execute(
        select(NeuronModel).where(
            NeuronModel.id == document.neuron_id,
            NeuronModel.owner_id == user.id
        )
    )
    neuron_model = neuron_result.scalar_one_or_none()

    if not neuron_model:
        raise HTTPException(status_code=404, detail="Neuron not found")

    # Get Neuron with Axon
    manager = await get_neuron_manager()
    neuron = await manager.get_neuron(document.neuron_id)

    if neuron and neuron.axon:
        # Delete from Axon (all chunks)
        for i in range(document.chunk_count):
            chunk_id = f"{document_id}_chunk_{i}"
            try:
                await neuron.axon.delete_document(chunk_id)
            except Exception as e:
                logger.warning(f"Failed to delete chunk {chunk_id}: {e}")

    # Delete from database
    await db.delete(document)
    await db.commit()

    # Audit log
    await log_audit_event(
        db=db,
        event_type="rag",
        action="delete_document",
        user_id=user.id,
        neuron_id=document.neuron_id,
        result="success",
        details={"document_id": document_id}
    )

    return {"message": "Document deleted successfully"}
