"""Student profile, academic record, project and certification logic (tenant scoped)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models import (
    AcademicRecord,
    Certification,
    Department,
    FacultyAssignment,
    Project,
    Student,
    User,
    UserRole,
)
from app.schemas.student import (
    AcademicRecordCreate,
    AcademicRecordResponse,
    AcademicRecordUpdate,
    CertificationCreate,
    CertificationResponse,
    ProjectCreate,
    ProjectResponse,
    StudentDetailResponse,
    StudentResponse,
    StudentUpdate,
)
from app.services import audit_service, department_service

STAFF_READ = "STUDENT_RECORD_READ"


def get_or_create_me(db: Session, user: User) -> Student:
    """Return the caller's Student row, creating an empty one on first use."""
    student = db.execute(
        select(Student).where(Student.user_id == user.id, Student.college_id == user.college_id)
    ).scalar_one_or_none()
    if student is None:
        student = Student(user_id=user.id, college_id=user.college_id)
        db.add(student)
        db.flush()
        audit_service.record(
            db,
            "STUDENT_CREATE",
            "student",
            user_id=user.id,
            college_id=user.college_id,
            resource_id=student.id,
        )
        db.commit()
    return student


def to_response(db: Session, student: Student) -> StudentResponse:
    """Build a StudentResponse including department name and completeness."""
    dept_name: str | None = None
    if student.department_id is not None:
        dept_name = db.execute(
            select(Department.name).where(
                Department.id == student.department_id,
                Department.college_id == student.college_id,
            )
        ).scalar_one_or_none()
    return StudentResponse(
        id=student.id,
        user_id=student.user_id,
        college_id=student.college_id,
        department_id=student.department_id,
        department_name=dept_name,
        roll_number=student.roll_number,
        graduation_year=student.graduation_year,
        phone=student.phone,
        profile_complete=bool(
            student.department_id and student.roll_number and student.graduation_year
        ),
    )


def update_me(db: Session, user: User, data: StudentUpdate) -> Student:
    """Update the caller's profile with department and roll-number validation."""
    student = get_or_create_me(db, user)
    fields = data.model_dump(exclude_unset=True)
    if fields.get("department_id") is not None:
        dept = department_service.get_in_college(db, user.college_id, fields["department_id"])
        if not dept.is_active:
            raise NotFoundError("Department not found")
    roll = fields.get("roll_number")
    if roll is not None:
        roll = roll.strip()
        fields["roll_number"] = roll
        clash = db.execute(
            select(Student.id).where(
                Student.college_id == user.college_id,
                Student.roll_number == roll,
                Student.id != student.id,
            )
        ).first()
        if clash is not None:
            raise ConflictError("Roll number already in use")
    for key, value in fields.items():
        setattr(student, key, value)
    audit_service.record(
        db,
        "STUDENT_UPDATE",
        "student",
        user_id=user.id,
        college_id=user.college_id,
        resource_id=student.id,
        metadata={"fields": sorted(fields)},
    )
    db.commit()
    return student


def list_records(db: Session, student: Student) -> list[AcademicRecord]:
    """Academic records of a student ordered by semester."""
    stmt = (
        select(AcademicRecord)
        .where(
            AcademicRecord.student_id == student.id,
            AcademicRecord.college_id == student.college_id,
        )
        .order_by(AcademicRecord.semester)
    )
    return list(db.execute(stmt).scalars())


def _semester_taken(db: Session, student: Student, semester: int, exclude: int | None) -> bool:
    stmt = select(AcademicRecord.id).where(
        AcademicRecord.student_id == student.id,
        AcademicRecord.college_id == student.college_id,
        AcademicRecord.semester == semester,
    )
    if exclude is not None:
        stmt = stmt.where(AcademicRecord.id != exclude)
    return db.execute(stmt).first() is not None


def create_record(
    db: Session, user: User, student: Student, data: AcademicRecordCreate
) -> AcademicRecord:
    """Create an academic record; duplicate semester -> 409."""
    if _semester_taken(db, student, data.semester, None):
        raise ConflictError("Record for this semester already exists")
    rec = AcademicRecord(
        student_id=student.id,
        college_id=student.college_id,
        semester=data.semester,
        cgpa=data.cgpa,
        active_arrears=data.active_arrears,
        attendance_pct=data.attendance_pct,
    )
    db.add(rec)
    db.flush()
    audit_service.record(
        db,
        "ACADEMIC_RECORD_CREATE",
        "academic_record",
        user_id=user.id,
        college_id=user.college_id,
        resource_id=rec.id,
    )
    db.commit()
    return rec


def update_record(
    db: Session, user: User, student: Student, record_id: int, data: AcademicRecordUpdate
) -> AcademicRecord:
    """Update one of the student's own academic records."""
    rec = db.execute(
        select(AcademicRecord).where(
            AcademicRecord.id == record_id,
            AcademicRecord.student_id == student.id,
            AcademicRecord.college_id == student.college_id,
        )
    ).scalar_one_or_none()
    if rec is None:
        raise NotFoundError("Academic record not found")
    fields = data.model_dump(exclude_unset=True)
    if fields.get("semester") is not None and _semester_taken(
        db, student, fields["semester"], rec.id
    ):
        raise ConflictError("Record for this semester already exists")
    for key, value in fields.items():
        if value is None and key != "attendance_pct":
            continue
        setattr(rec, key, value)
    audit_service.record(
        db,
        "ACADEMIC_RECORD_UPDATE",
        "academic_record",
        user_id=user.id,
        college_id=user.college_id,
        resource_id=rec.id,
    )
    db.commit()
    return rec


def list_projects(db: Session, student: Student) -> list[Project]:
    """Projects of a student."""
    stmt = (
        select(Project)
        .where(Project.student_id == student.id, Project.college_id == student.college_id)
        .order_by(Project.id)
    )
    return list(db.execute(stmt).scalars())


def create_project(db: Session, user: User, student: Student, data: ProjectCreate) -> Project:
    """Create a project for the student."""
    obj = Project(
        student_id=student.id,
        college_id=student.college_id,
        title=data.title.strip(),
        description=data.description,
        skills=list(data.skills),
        url=data.url,
    )
    db.add(obj)
    db.flush()
    audit_service.record(
        db,
        "PROJECT_CREATE",
        "project",
        user_id=user.id,
        college_id=user.college_id,
        resource_id=obj.id,
    )
    db.commit()
    return obj


def delete_project(db: Session, user: User, student: Student, project_id: int) -> None:
    """Delete one of the student's own projects."""
    obj = db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.student_id == student.id,
            Project.college_id == student.college_id,
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NotFoundError("Project not found")
    db.delete(obj)
    audit_service.record(
        db,
        "PROJECT_DELETE",
        "project",
        user_id=user.id,
        college_id=user.college_id,
        resource_id=project_id,
    )
    db.commit()


def list_certifications(db: Session, student: Student) -> list[Certification]:
    """Certifications of a student."""
    stmt = (
        select(Certification)
        .where(
            Certification.student_id == student.id,
            Certification.college_id == student.college_id,
        )
        .order_by(Certification.id)
    )
    return list(db.execute(stmt).scalars())


def create_certification(
    db: Session, user: User, student: Student, data: CertificationCreate
) -> Certification:
    """Create a certification for the student."""
    obj = Certification(
        student_id=student.id,
        college_id=student.college_id,
        name=data.name.strip(),
        issuer=data.issuer,
        issued_on=data.issued_on,
    )
    db.add(obj)
    db.flush()
    audit_service.record(
        db,
        "CERTIFICATION_CREATE",
        "certification",
        user_id=user.id,
        college_id=user.college_id,
        resource_id=obj.id,
    )
    db.commit()
    return obj


def delete_certification(db: Session, user: User, student: Student, cert_id: int) -> None:
    """Delete one of the student's own certifications."""
    obj = db.execute(
        select(Certification).where(
            Certification.id == cert_id,
            Certification.student_id == student.id,
            Certification.college_id == student.college_id,
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NotFoundError("Certification not found")
    db.delete(obj)
    audit_service.record(
        db,
        "CERTIFICATION_DELETE",
        "certification",
        user_id=user.id,
        college_id=user.college_id,
        resource_id=cert_id,
    )
    db.commit()


def get_accessible_student(db: Session, caller: User, student_id: int) -> Student:
    """Return the Student row if the caller may see it, else raise (no audit, no commit).

    Access matrix: STUDENT only own id; FACULTY only assigned students; TPO and ADMIN any
    student in the same college. HOD and SUPER_ADMIN are denied for now.

    OPEN QUESTION: HOD access needs a HOD-to-department mapping which does not exist yet;
    SUPER_ADMIN cross-college access is likewise undecided. Both stay denied until decided.
    """
    role = caller.role
    if role not in (UserRole.STUDENT, UserRole.FACULTY, UserRole.TPO, UserRole.ADMIN):
        raise ForbiddenError("Insufficient permissions")
    student = db.execute(
        select(Student).where(Student.id == student_id, Student.college_id == caller.college_id)
    ).scalar_one_or_none()
    if student is None:
        raise NotFoundError("Student not found")
    if role == UserRole.STUDENT:
        if student.user_id != caller.id:
            raise NotFoundError("Student not found")
    elif role == UserRole.FACULTY:
        assigned = db.execute(
            select(FacultyAssignment.id).where(
                FacultyAssignment.college_id == caller.college_id,
                FacultyAssignment.faculty_user_id == caller.id,
                FacultyAssignment.student_id == student.id,
            )
        ).first()
        if assigned is None:
            raise NotFoundError("Student not found")
    return student


def get_detail(db: Session, caller: User, student_id: int) -> StudentDetailResponse:
    """Return a student's full record if the caller is allowed to see it (audited for staff)."""
    role = caller.role
    student = get_accessible_student(db, caller, student_id)
    if role != UserRole.STUDENT:
        audit_service.record(
            db,
            STAFF_READ,
            "student",
            user_id=caller.id,
            college_id=caller.college_id,
            resource_id=student.id,
        )
        db.commit()
    return StudentDetailResponse(
        profile=to_response(db, student),
        academic_records=[
            AcademicRecordResponse.model_validate(r) for r in list_records(db, student)
        ],
        projects=[ProjectResponse.model_validate(p) for p in list_projects(db, student)],
        certifications=[
            CertificationResponse.model_validate(c) for c in list_certifications(db, student)
        ],
    )
