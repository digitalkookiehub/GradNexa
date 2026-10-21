"""ADMIN/TPO company management."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from app.models import User, UserRole
from app.schemas.job_admin import CompanyCreate, CompanyOut, CompanyUpdate
from app.services import company_service as svc

router = APIRouter(prefix="/admin/companies", tags=["admin-companies"])
Staff = Depends(require_role(UserRole.ADMIN, UserRole.TPO))


@router.get("", response_model=list[CompanyOut])
async def list_companies(user: User = Staff, db: Session = Depends(get_db)) -> list[CompanyOut]:
    """All companies of the college."""
    return svc.list_companies(db, user.college_id)


@router.post("", response_model=CompanyOut, status_code=201)
async def create_company(
    payload: CompanyCreate, user: User = Staff, db: Session = Depends(get_db)
) -> CompanyOut:
    """Create a company."""
    return svc.to_out(db, svc.create_company(db, user, payload))


@router.put("/{company_id}", response_model=CompanyOut)
async def update_company(
    company_id: int, payload: CompanyUpdate, user: User = Staff, db: Session = Depends(get_db)
) -> CompanyOut:
    """Update a company."""
    return svc.to_out(db, svc.update_company(db, user, company_id, payload))


@router.delete("/{company_id}", status_code=204)
async def delete_company(
    company_id: int, user: User = Staff, db: Session = Depends(get_db)
) -> Response:
    """Delete a company without job postings."""
    svc.delete_company(db, user, company_id)
    return Response(status_code=204)
