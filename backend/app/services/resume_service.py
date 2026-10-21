"""Resume upload, storage and deterministic analysis (student-only, tenant scoped).

Staff cannot read resumes in this phase (open privacy question). The resume score never feeds
readiness. The LLM-based extractor is Not implemented in this phase.
"""
import hashlib
import re
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import NotFoundError
from app.models import CareerRole, Resume, ResumeAnalysis, RoleSkill, Skill, Student, User
from app.schemas.resume import (
    AnalysisResponse,
    AnalysisSummary,
    AnalyzeRequest,
    ResumeResponse,
)
from app.services import audit_service, career_role_service, job_student_service, resume_extractor
from app.services.file_storage import FileStorage, get_storage
from app.services.resume_extractor import RoleSkillIn
from app.services.resume_text import PayloadTooLargeError, UnprocessableError, parse_upload

NO_TEXT_NOTE = (
    "No extractable text found (scanned documents are not supported - "
    "OCR is not implemented in this phase)"
)
NO_SKILLS_NOTE = "No skills are configured for your college, so no skills could be matched"
NO_SECTIONS_NOTE = "No standard section headings were detected in the resume text"
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def sanitise_filename(name: str | None) -> str:
    """Display-only filename: no path parts, control chars or separators, max 255 chars."""
    base = re.split(r"[\\/]", name or "")[-1]
    base = _CONTROL.sub("", base).strip().strip(".") or "resume"
    return base[:255]


def _own(db: Session, student: Student, resume_id: int) -> Resume:
    resume = db.execute(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.student_id == student.id,
            Resume.college_id == student.college_id,
        )
    ).scalar_one_or_none()
    if resume is None:
        raise NotFoundError("Resume not found")
    return resume


def to_response(resume: Resume) -> ResumeResponse:
    """Map a Resume row to its API shape."""
    return ResumeResponse(
        id=resume.id,
        original_filename=resume.original_filename,
        content_type=resume.content_type,
        size_bytes=resume.size_bytes,
        page_count=resume.page_count,
        uploaded_at=resume.uploaded_at,
        has_text=bool(resume.extracted_text.strip()),
        text_length=len(resume.extracted_text),
    )


def upload(
    db: Session,
    user: User,
    student: Student,
    filename: str | None,
    data: bytes,
    storage: FileStorage | None = None,
) -> Resume:
    """Validate by content, store the file under a random key and persist metadata."""
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if not data:
        raise UnprocessableError("The uploaded file is empty")
    if len(data) > max_bytes:
        raise PayloadTooLargeError(f"File exceeds the {settings.MAX_UPLOAD_MB} MB limit")
    parsed = parse_upload(data)
    store = storage or get_storage()
    key = store.save(student.college_id, data)
    resume = Resume(
        student_id=student.id,
        college_id=student.college_id,
        original_filename=sanitise_filename(filename),
        content_type=parsed.content_type,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        storage_key=key,
        extracted_text=parsed.text,
        page_count=parsed.page_count,
    )
    try:
        db.add(resume)
        db.flush()
        audit_service.record(
            db, "RESUME_UPLOAD", "resume", user_id=user.id, college_id=user.college_id,
            resource_id=resume.id,
            metadata={"size_bytes": len(data), "content_type": parsed.content_type},
        )
        db.commit()
    except Exception:
        db.rollback()
        store.delete(key)
        raise
    return resume


def list_resumes(db: Session, student: Student) -> list[Resume]:
    """Own resumes, newest first."""
    stmt = (
        select(Resume)
        .where(Resume.student_id == student.id, Resume.college_id == student.college_id)
        .order_by(Resume.uploaded_at.desc(), Resume.id.desc())
    )
    return list(db.execute(stmt).scalars())


def get_resume(db: Session, student: Student, resume_id: int) -> Resume:
    """Own resume or NotFoundError."""
    return _own(db, student, resume_id)


def delete_resume(
    db: Session, user: User, student: Student, resume_id: int, storage: FileStorage | None = None
) -> None:
    """Delete the resume, its analyses and the stored file."""
    resume = _own(db, student, resume_id)
    key = resume.storage_key
    db.execute(
        delete(ResumeAnalysis).where(
            ResumeAnalysis.resume_id == resume.id, ResumeAnalysis.college_id == student.college_id
        )
    )
    db.delete(resume)
    audit_service.record(
        db, "RESUME_DELETE", "resume", user_id=user.id, college_id=user.college_id,
        resource_id=resume_id,
    )
    db.commit()
    (storage or get_storage()).delete(key)


def _college_skills(db: Session, college_id: int) -> list[tuple[int, str]]:
    rows = db.execute(
        select(Skill.id, Skill.name).where(Skill.college_id == college_id).order_by(Skill.id)
    ).all()
    return [(int(i), str(n)) for i, n in rows]


def _role_skills(db: Session, college_id: int, role_id: int) -> list[RoleSkillIn]:
    stmt = (
        select(RoleSkill.skill_id, Skill.name, RoleSkill.required_level, RoleSkill.weight)
        .join(Skill, Skill.id == RoleSkill.skill_id)
        .where(
            RoleSkill.role_id == role_id,
            RoleSkill.college_id == college_id,
            Skill.college_id == college_id,
        )
        .order_by(Skill.name, Skill.id)
    )
    return [
        RoleSkillIn(
            skill_id=int(sid), skill_name=str(name),
            required_level=float(level), weight=float(weight),
        )
        for sid, name, level, weight in db.execute(stmt).all()
    ]


def analyze(
    db: Session, user: User, student: Student, resume_id: int, data: AnalyzeRequest
) -> ResumeAnalysis:
    """Run the deterministic extractor and store the result."""
    resume = _own(db, student, resume_id)
    role: CareerRole | None = None
    if data.role_id is not None:
        role = career_role_service.get_visible_role(db, student, data.role_id)
    text = resume.extracted_text
    has_text = bool(text.strip())
    skills = _college_skills(db, student.college_id)
    notes: list[str] = []

    extracted = resume_extractor.extract(text, skills)
    skill_ids = {int(s["skill_id"]) for s in extracted["skills"]}
    if not has_text:
        notes.append(NO_TEXT_NOTE)
    else:
        if not skills:
            notes.append(NO_SKILLS_NOTE)
        if not extracted["sections_found"]:
            notes.append(NO_SECTIONS_NOTE)

    role_match: dict[str, Any] | None = None
    if role is not None:
        role_match = resume_extractor.role_match(
            skill_ids, _role_skills(db, student.college_id, role.id)
        )
        if not role_match["found"] and not role_match["missing"]:
            notes.append("The selected role has no skills configured")
        if not has_text:
            role_match["match_percent"] = None

    jd_match: dict[str, Any] | None = None
    jd = (data.jd_text or "").strip()
    if data.job_id is not None:
        job = job_student_service.get_open_job(db, student, data.job_id)
        required = sorted(
            job_student_service.job_requirements(db, job), key=lambda r: (r.skill_name, r.skill_id)
        )
        items: list[dict[str, Any]] = [
            {
                "skill_id": r.skill_id,
                "skill_name": r.skill_name,
                "in_resume": r.skill_id in skill_ids,
            }
            for r in required
        ]
        seen = {i["skill_id"] for i in items}
        for hit in resume_extractor.jd_match(job.body, skills, skill_ids)["skills_in_jd"]:
            if hit["skill_id"] not in seen:
                items.append(hit)
                seen.add(hit["skill_id"])
        jd_match = {
            "match_percent": (
                round(sum(1 for i in items if i["in_resume"]) / len(items) * 100, 2)
                if items
                else None
            ),
            "skills_in_jd": items,
            "job_id": job.id,
            "job_title": job.title,
        }
        if not items:
            notes.append("The selected job has no skills configured or found in its description")
        if not has_text:
            jd_match["match_percent"] = None
    elif jd:
        jd_match = resume_extractor.jd_match(jd, skills, skill_ids)
        if not jd_match["skills_in_jd"]:
            notes.append("No configured skills were found in the job description")
        if not has_text:
            jd_match["match_percent"] = None

    row = ResumeAnalysis(
        resume_id=resume.id,
        student_id=student.id,
        college_id=student.college_id,
        role_id=role.id if role else None,
        extractor_version=resume_extractor.EXTRACTOR_VERSION,
        extracted=extracted,
        role_match=role_match,
        jd_match=jd_match,
        notes=notes,
    )
    db.add(row)
    db.flush()
    audit_service.record(
        db, "RESUME_ANALYZE", "resume", user_id=user.id, college_id=user.college_id,
        resource_id=resume.id,
        metadata={"analysis_id": row.id, "role_id": row.role_id, "has_jd": jd_match is not None},
    )
    db.commit()
    return row


def _role_name(db: Session, college_id: int, role_id: int | None) -> str | None:
    if role_id is None:
        return None
    return db.execute(
        select(CareerRole.name).where(
            CareerRole.id == role_id, CareerRole.college_id == college_id
        )
    ).scalar_one_or_none()


def to_analysis_response(db: Session, row: ResumeAnalysis) -> AnalysisResponse:
    """Map an analysis row to its API shape."""
    return AnalysisResponse.model_validate(
        {
            "id": row.id,
            "resume_id": row.resume_id,
            "role_id": row.role_id,
            "role_name": _role_name(db, row.college_id, row.role_id),
            "extractor_version": row.extractor_version,
            "created_at": row.created_at,
            "extracted": row.extracted,
            "role_match": row.role_match,
            "jd_match": row.jd_match,
            "notes": list(row.notes),
            "job_id": (row.jd_match or {}).get("job_id"),
            "job_title": (row.jd_match or {}).get("job_title"),
        }
    )


def _analyses(db: Session, student: Student, resume_id: int) -> list[ResumeAnalysis]:
    _own(db, student, resume_id)
    stmt = (
        select(ResumeAnalysis)
        .where(
            ResumeAnalysis.resume_id == resume_id,
            ResumeAnalysis.student_id == student.id,
            ResumeAnalysis.college_id == student.college_id,
        )
        .order_by(ResumeAnalysis.created_at.desc(), ResumeAnalysis.id.desc())
    )
    return list(db.execute(stmt).scalars())


def latest_analysis(db: Session, student: Student, resume_id: int) -> AnalysisResponse:
    """Latest analysis or NotFoundError."""
    rows = _analyses(db, student, resume_id)
    if not rows:
        raise NotFoundError("No analysis found for this resume")
    return to_analysis_response(db, rows[0])


def list_analyses(db: Session, student: Student, resume_id: int) -> list[AnalysisSummary]:
    """Analysis history, newest first."""
    return [
        AnalysisSummary(
            id=r.id,
            created_at=r.created_at,
            role_name=_role_name(db, r.college_id, r.role_id),
            has_jd=r.jd_match is not None,
            role_match_percent=(r.role_match or {}).get("match_percent"),
        )
        for r in _analyses(db, student, resume_id)
    ]
