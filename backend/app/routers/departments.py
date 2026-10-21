"""Department listing endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import TenantContext, get_db, get_tenant
from app.models import Department
from app.schemas.department import DepartmentResponse
from app.services import department_service

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentResponse])
async def list_departments(
    tenant: TenantContext = Depends(get_tenant), db: Session = Depends(get_db)
) -> list[Department]:
    """Active departments of the caller's college."""
    return department_service.list_active(db, tenant.college_id)
