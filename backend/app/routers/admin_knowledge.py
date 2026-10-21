"""ADMIN/FACULTY knowledge document management; approve/archive are ADMIN only."""
from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db, require_role
from app.models import RagDocumentStatus, RagSourceType, User, UserRole
from app.schemas.knowledge import ChunkListResponse, DocumentResponse, DocumentUpdate
from app.services import knowledge_service as svc
from app.services.resume_text import PayloadTooLargeError

router = APIRouter(prefix="/admin/knowledge-documents", tags=["admin-knowledge"])
Staff = Depends(require_role(UserRole.ADMIN, UserRole.FACULTY))
AdminUser = Depends(require_role(UserRole.ADMIN))
_MULTIPART_SLACK = 1024 * 1024


@router.post("", response_model=DocumentResponse, status_code=201)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=255),
    source_type: RagSourceType = Form(...),
    department_id: int | None = Form(default=None),
    user: User = Staff,
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """Upload a PDF, DOCX, TXT or MD document; it starts PENDING and is not retrievable."""
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > max_bytes + _MULTIPART_SLACK:
        raise PayloadTooLargeError(f"File exceeds the {settings.MAX_UPLOAD_MB} MB limit")
    data = await file.read(max_bytes + 1)
    doc = svc.upload(
        db, user, filename=file.filename, data=data, title=title,
        source_type=source_type, department_id=department_id,
    )
    return svc.to_response(db, doc)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    status: RagDocumentStatus | None = None,
    source_type: RagSourceType | None = None,
    user: User = Staff,
    db: Session = Depends(get_db),
) -> list[DocumentResponse]:
    """Documents of the college."""
    return [
        svc.to_response(db, d)
        for d in svc.list_documents(db, user.college_id, status, source_type)
    ]


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: int, user: User = Staff, db: Session = Depends(get_db)
) -> DocumentResponse:
    """One document."""
    return svc.to_response(db, svc.get_document(db, user.college_id, doc_id))


@router.get("/{doc_id}/chunks", response_model=ChunkListResponse)
async def get_chunks(
    doc_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Staff,
    db: Session = Depends(get_db),
) -> ChunkListResponse:
    """Stored chunks of a document."""
    return svc.list_chunks(db, user.college_id, doc_id, limit, offset)


@router.put("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: int, payload: DocumentUpdate, user: User = Staff, db: Session = Depends(get_db)
) -> DocumentResponse:
    """Update title, source type or department (metadata only)."""
    return svc.to_response(db, svc.update_metadata(db, user, doc_id, payload))


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: int, user: User = Staff, db: Session = Depends(get_db)
) -> Response:
    """Delete a document, its chunks and its stored file."""
    svc.delete_document(db, user, doc_id)
    return Response(status_code=204)


@router.post("/{doc_id}/approve", response_model=DocumentResponse)
async def approve_document(
    doc_id: int, user: User = AdminUser, db: Session = Depends(get_db)
) -> DocumentResponse:
    """Approve a document for retrieval."""
    return svc.to_response(db, svc.approve(db, user, doc_id))


@router.post("/{doc_id}/archive", response_model=DocumentResponse)
async def archive_document(
    doc_id: int, user: User = AdminUser, db: Session = Depends(get_db)
) -> DocumentResponse:
    """Archive a document (removes it from retrieval)."""
    return svc.to_response(db, svc.archive(db, user, doc_id))
