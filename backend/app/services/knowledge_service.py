"""Knowledge document management: upload, review workflow, metadata, chunks, search wrapper.

Every query is scoped by college_id. Only ADMIN may approve/archive (enforced in the router).
Raw files are never served; storage is used for ingestion records and deletion only.
"""
import hashlib
import logging
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import NotFoundError
from app.models import (
    Department,
    RAGChunk,
    RAGDocument,
    RagDocumentStatus,
    RagSourceType,
    Student,
    User,
    UserRole,
)
from app.schemas.knowledge import (
    ChunkItem,
    ChunkListResponse,
    DocumentResponse,
    DocumentUpdate,
    PassageResponse,
    SearchResponse,
)
from app.services import audit_service, department_service, rag_ingest, retrieval_service
from app.services.file_storage import FileStorage, get_storage
from app.services.resume_service import sanitise_filename
from app.services.resume_text import PayloadTooLargeError

logger = logging.getLogger(__name__)


def to_response(db: Session, doc: RAGDocument) -> DocumentResponse:
    """Map a document row to its API shape (department name resolved within the college)."""
    name: str | None = None
    if doc.department_id is not None:
        name = db.execute(
            select(Department.name).where(
                Department.id == doc.department_id, Department.college_id == doc.college_id
            )
        ).scalar_one_or_none()
    return DocumentResponse(
        id=doc.id, title=doc.title, source_type=doc.source_type,
        department_id=doc.department_id, department_name=name,
        original_filename=doc.original_filename, content_type=doc.content_type,
        size_bytes=doc.size_bytes, status=doc.status, uploaded_by=doc.uploaded_by,
        approved_by=doc.approved_by, approved_at=doc.approved_at,
        chunk_count=doc.chunk_count, created_at=doc.created_at,
    )


def get_document(db: Session, college_id: int, doc_id: int) -> RAGDocument:
    """Document of the college or 404."""
    doc = db.execute(
        select(RAGDocument).where(RAGDocument.id == doc_id, RAGDocument.college_id == college_id)
    ).scalar_one_or_none()
    if doc is None:
        raise NotFoundError("Document not found")
    return doc


def upload(
    db: Session,
    user: User,
    *,
    filename: str | None,
    data: bytes,
    title: str,
    source_type: RagSourceType,
    department_id: int | None,
    storage: FileStorage | None = None,
) -> RAGDocument:
    """Validate by content, chunk, store the file and persist document + chunks as PENDING."""
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise PayloadTooLargeError(f"File exceeds the {settings.MAX_UPLOAD_MB} MB limit")
    if department_id is not None:
        department_service.get_in_college(db, user.college_id, department_id)
    result = rag_ingest.ingest(data, filename)
    store = storage or get_storage()
    key = store.save(user.college_id, data)
    doc = RAGDocument(
        college_id=user.college_id, title=title.strip(), source_type=source_type,
        department_id=department_id, original_filename=sanitise_filename(filename),
        content_type=result.content_type, size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(), storage_key=key,
        status=RagDocumentStatus.PENDING, uploaded_by=user.id,
        chunk_count=len(result.chunks),
    )
    try:
        db.add(doc)
        db.flush()
        db.add_all(
            RAGChunk(
                document_id=doc.id, college_id=user.college_id, chunk_index=c.index,
                content=c.content, token_count=len(c.content.split()),
                char_start=c.char_start, char_end=c.char_end,
                chunk_metadata={"heading": c.heading},
            )
            for c in result.chunks
        )
        audit_service.record(
            db, "KNOWLEDGE_UPLOAD", "rag_document", user_id=user.id,
            college_id=user.college_id, resource_id=doc.id,
            metadata={"size_bytes": len(data), "chunks": len(result.chunks)},
        )
        db.commit()
    except Exception:
        db.rollback()
        store.delete(key)
        raise
    return doc


def list_documents(
    db: Session,
    college_id: int,
    status: RagDocumentStatus | None,
    source_type: RagSourceType | None,
) -> list[RAGDocument]:
    """Documents of the college, newest first."""
    stmt = select(RAGDocument).where(RAGDocument.college_id == college_id)
    if status is not None:
        stmt = stmt.where(RAGDocument.status == status)
    if source_type is not None:
        stmt = stmt.where(RAGDocument.source_type == source_type)
    return list(
        db.execute(stmt.order_by(RAGDocument.created_at.desc(), RAGDocument.id.desc()))
        .scalars()
    )


def list_chunks(
    db: Session, college_id: int, doc_id: int, limit: int, offset: int
) -> ChunkListResponse:
    """Paged chunks of a document of the college."""
    get_document(db, college_id, doc_id)
    base = (RAGChunk.document_id == doc_id, RAGChunk.college_id == college_id)
    total = db.execute(select(func.count(RAGChunk.id)).where(*base)).scalar_one()
    rows = db.execute(
        select(RAGChunk).where(*base).order_by(RAGChunk.chunk_index).limit(limit).offset(offset)
    ).scalars()
    return ChunkListResponse(
        total=total,
        chunks=[
            ChunkItem(
                id=c.id, chunk_index=c.chunk_index, content=c.content,
                heading=(c.chunk_metadata or {}).get("heading"),
            )
            for c in rows
        ],
    )


def update_metadata(db: Session, user: User, doc_id: int, payload: DocumentUpdate) -> RAGDocument:
    """Metadata-only update (any status). Explicit null department clears it."""
    doc = get_document(db, user.college_id, doc_id)
    fields = payload.model_fields_set
    if "title" in fields and payload.title is not None:
        doc.title = payload.title
    if "source_type" in fields and payload.source_type is not None:
        doc.source_type = payload.source_type
    if "department_id" in fields:
        if payload.department_id is not None:
            department_service.get_in_college(db, user.college_id, payload.department_id)
        doc.department_id = payload.department_id
    audit_service.record(
        db, "KNOWLEDGE_UPDATE", "rag_document", user_id=user.id, college_id=user.college_id,
        resource_id=doc.id, metadata={"fields": sorted(fields)},
    )
    db.commit()
    return doc


def approve(db: Session, user: User, doc_id: int) -> RAGDocument:
    """PENDING or ARCHIVED -> APPROVED."""
    doc = get_document(db, user.college_id, doc_id)
    doc.status = RagDocumentStatus.APPROVED
    doc.approved_by = user.id
    doc.approved_at = datetime.now(UTC)
    audit_service.record(
        db, "KNOWLEDGE_APPROVE", "rag_document", user_id=user.id,
        college_id=user.college_id, resource_id=doc.id,
    )
    db.commit()
    return doc


def archive(db: Session, user: User, doc_id: int) -> RAGDocument:
    """APPROVED or PENDING -> ARCHIVED (no longer retrievable)."""
    doc = get_document(db, user.college_id, doc_id)
    doc.status = RagDocumentStatus.ARCHIVED
    audit_service.record(
        db, "KNOWLEDGE_ARCHIVE", "rag_document", user_id=user.id,
        college_id=user.college_id, resource_id=doc.id,
    )
    db.commit()
    return doc


def delete_document(
    db: Session, user: User, doc_id: int, storage: FileStorage | None = None
) -> None:
    """Remove chunks, the document row and the stored file."""
    doc = get_document(db, user.college_id, doc_id)
    key = doc.storage_key
    db.execute(
        delete(RAGChunk).where(
            RAGChunk.document_id == doc.id, RAGChunk.college_id == doc.college_id
        )
    )
    db.delete(doc)
    audit_service.record(
        db, "KNOWLEDGE_DELETE", "rag_document", user_id=user.id, college_id=user.college_id,
        resource_id=doc_id,
    )
    db.commit()
    (storage or get_storage()).delete(key)


def search_for_user(db: Session, user: User, query: str, top_k: int) -> SearchResponse:
    """Search as the caller. Students see own-department + unscoped docs; staff see all."""
    department_id: int | None = None
    all_departments = user.role != UserRole.STUDENT
    if not all_departments:
        department_id = db.execute(
            select(Student.department_id).where(
                Student.user_id == user.id, Student.college_id == user.college_id
            )
        ).scalar_one_or_none()
    result = retrieval_service.search(
        db, college_id=user.college_id, department_id=department_id, query=query,
        top_k=top_k, all_departments=all_departments,
    )
    audit_service.record(
        db, "KNOWLEDGE_SEARCH", "rag_search", user_id=user.id, college_id=user.college_id,
        metadata={
            "query_length": len(query), "results": len(result.passages),
            "insufficient_evidence": result.insufficient_evidence,
        },
    )
    db.commit()
    return SearchResponse(
        query=query,
        insufficient_evidence=result.insufficient_evidence,
        message=result.message,
        passages=[PassageResponse(**p.__dict__) for p in result.passages],
    )
