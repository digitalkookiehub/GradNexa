"""Code-defined MCP tool registry and the single audited, authorised call path."""
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import AppError, ForbiddenError, NotFoundError, UnprocessableError
from app.mcp import schemas as s
from app.mcp import tools as t
from app.models import MCPTool, User, UserRole
from app.services import audit_service

logger = logging.getLogger(__name__)

MCP_TOOL_CALL = "MCP_TOOL_CALL"
MCP_TOOL_TOGGLE = "MCP_TOOL_TOGGLE"

Handler = Callable[[Session, User, Any], BaseModel]

STUDENT_LEVEL_ROLES = frozenset({UserRole.STUDENT, UserRole.FACULTY, UserRole.TPO, UserRole.ADMIN})
ALL_ROLES = frozenset(UserRole)


@dataclass(frozen=True)
class ToolDef:
    """One read-only tool: schemas, allowed roles and handler."""

    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    allowed_roles: frozenset[UserRole]
    handler: Handler


_TOOLS: list[ToolDef] = [
    ToolDef(
        "get_student_profile",
        "Student profile (name, department, roll number, graduation year).",
        s.StudentIn, s.ProfileOut, STUDENT_LEVEL_ROLES, t.get_student_profile,
    ),
    ToolDef(
        "get_student_academic_record",
        "Semester CGPA, active arrears and attendance.",
        s.StudentIn, s.AcademicRecordOut, STUDENT_LEVEL_ROLES, t.get_student_academic_record,
    ),
    ToolDef(
        "get_student_assessment_results",
        "Recent submitted assessment results.",
        s.AssessmentResultsIn, s.AssessmentResultsOut, STUDENT_LEVEL_ROLES,
        t.get_student_assessment_results,
    ),
    ToolDef(
        "get_student_skill_scores",
        "Stored skill scores with evidence counts.",
        s.StudentIn, s.SkillScoresOut, STUDENT_LEVEL_ROLES, t.get_student_skill_scores,
    ),
    ToolDef(
        "get_student_progress",
        "Active learning plan progress and the latest stored readiness summary "
        "(with gaps when role_id is given).",
        s.ProgressIn, s.ProgressOut, STUDENT_LEVEL_ROLES, t.get_student_progress,
    ),
    ToolDef(
        "get_department_details",
        "Department details and its active career roles.",
        s.DepartmentIn, s.DepartmentOut, ALL_ROLES, t.get_department_details,
    ),
    ToolDef(
        "get_eligibility_rules",
        "Configured eligibility criteria of a job (plus the student's evaluation when a "
        "student is resolvable).",
        s.JobEligibilityIn, s.EligibilityRulesOut, ALL_ROLES, t.get_eligibility_rules,
    ),
    ToolDef(
        "get_company_requirements",
        "A company and the required skills of its open jobs.",
        s.CompanyIn, s.CompanyRequirementsOut, ALL_ROLES, t.get_company_requirements,
    ),
    ToolDef(
        "get_job_description",
        "Job description with required skills (open jobs only for students).",
        s.JobIn, s.JobDescriptionOut, ALL_ROLES, t.get_job_description,
    ),
]

REGISTRY: dict[str, ToolDef] = {d.name: d for d in _TOOLS}


def get_tool(name: str) -> ToolDef:
    """Tool by name or NotFoundError."""
    tool = REGISTRY.get(name)
    if tool is None:
        raise NotFoundError("Tool not found")
    return tool


def overrides(db: Session, college_id: int) -> dict[str, bool]:
    """Per-college enable overrides (default enabled when no row)."""
    rows = db.execute(
        select(MCPTool.name, MCPTool.is_enabled).where(MCPTool.college_id == college_id)
    ).all()
    return {str(n): bool(e) for n, e in rows}


def is_enabled(db: Session, college_id: int, name: str) -> bool:
    """Whether the tool is enabled for the college."""
    return overrides(db, college_id).get(name, True)


def tools_for_role(role: UserRole) -> list[ToolDef]:
    """Tools a role may use, in registry order."""
    return [d for d in REGISTRY.values() if role in d.allowed_roles]


def _validation_message(exc: ValidationError) -> str:
    parts = [
        ".".join(str(p) for p in e["loc"]) + ": " + str(e["msg"])
        for e in exc.errors(include_input=False, include_url=False)
    ]
    return "; ".join(parts) or "Invalid arguments"


def _audit(
    db: Session, user: User, name: str, keys: list[str], outcome: str, student_id: int | None
) -> None:
    meta: dict[str, Any] = {"tool": name, "argument_keys": keys, "outcome": outcome}
    if student_id is not None:
        meta["student_id"] = student_id
    audit_service.record(
        db, MCP_TOOL_CALL, "mcp_tool", user_id=user.id, college_id=user.college_id,
        resource_id=name, metadata=meta,
    )
    db.commit()


def call_tool(db: Session, user: User, name: str, arguments: dict[str, Any]) -> BaseModel:
    """Authorise, validate, run and audit one tool call; returns the validated output model."""
    tool = get_tool(name)
    keys = sorted(str(k) for k in arguments)
    try:
        if user.role not in tool.allowed_roles:
            raise ForbiddenError("Insufficient permissions")
        if not is_enabled(db, user.college_id, name):
            raise ForbiddenError("Tool disabled")
        try:
            args = tool.input_model.model_validate(arguments)
        except ValidationError as exc:
            raise UnprocessableError(_validation_message(exc)) from exc
        output = tool.handler(db, user, args)
        validated = tool.output_model.model_validate(output.model_dump())
    except AppError as exc:
        db.rollback()
        _audit(db, user, name, keys, f"error_{exc.status_code}", None)
        raise
    sid = getattr(validated, "student_id", None)
    _audit(db, user, name, keys, "ok", sid if isinstance(sid, int) else None)
    return validated
