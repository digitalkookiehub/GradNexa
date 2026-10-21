"""Tests for Phase 1: student profile, academic data, staff access, admin and seed script."""
import logging
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    College,
    Department,
    FacultyAssignment,
    Student,
    User,
    UserRole,
)
from scripts import seed_college

Headers = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


def _dept(db: Session, college: College, code: str = "CS", active: bool = True) -> Department:
    dept = Department(college_id=college.id, name=f"Dept {code}", code=code, is_active=active)
    db.add(dept)
    db.commit()
    return dept


def _student_row(db: Session, user: User) -> Student:
    row = Student(user_id=user.id, college_id=user.college_id)
    db.add(row)
    db.commit()
    return row


def _actions(db: Session) -> list[str]:
    return [a for (a,) in db.execute(select(AuditLog.action)).all()]


# ---- departments ------------------------------------------------------------------------


def test_departments_listing_scoped_and_active(
    client: TestClient, db: Session, college: College, other_college: College,
    users: dict[UserRole, User], auth_headers: Headers,
) -> None:
    """Only active departments of the caller's college are listed."""
    _dept(db, college, "CS")
    _dept(db, college, "OLD", active=False)
    _dept(db, other_college, "EE")
    resp = client.get("/api/v1/departments", headers=auth_headers(users[UserRole.HOD]))
    assert resp.status_code == 200
    assert [d["code"] for d in resp.json()] == ["CS"]
    assert client.get("/api/v1/departments").status_code == 401


# ---- profile ----------------------------------------------------------------------------


def test_profile_lazy_create_and_update(
    client: TestClient, db: Session, college: College, users: dict[UserRole, User],
    auth_headers: Headers,
) -> None:
    """GET creates an empty row; PUT completes the profile."""
    h = auth_headers(users[UserRole.STUDENT])
    first = client.get("/api/v1/students/me", headers=h).json()
    assert first["profile_complete"] is False
    assert first["department_name"] is None
    assert client.get("/api/v1/students/me", headers=h).json()["id"] == first["id"]
    dept = _dept(db, college)
    resp = client.put(
        "/api/v1/students/me",
        headers=h,
        json={"department_id": dept.id, "roll_number": "R1", "graduation_year": 2027,
              "phone": "99999"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["profile_complete"] is True
    assert body["department_name"] == "Dept CS"
    assert "STUDENT_UPDATE" in _actions(db)


def test_profile_partial_update_incomplete(
    client: TestClient, users: dict[UserRole, User], auth_headers: Headers
) -> None:
    """Profile without department is not complete."""
    h = auth_headers(users[UserRole.STUDENT])
    body = client.put("/api/v1/students/me", headers=h, json={"roll_number": "R9"}).json()
    assert body["profile_complete"] is False


@pytest.mark.parametrize("role", [UserRole.FACULTY, UserRole.TPO, UserRole.HOD, UserRole.ADMIN])
def test_me_student_only(
    client: TestClient, users: dict[UserRole, User], auth_headers: Headers, role: UserRole
) -> None:
    """Non-students cannot use /students/me."""
    assert client.get("/api/v1/students/me", headers=auth_headers(users[role])).status_code == 403


def test_profile_validation_bounds(
    client: TestClient, users: dict[UserRole, User], auth_headers: Headers
) -> None:
    """Out-of-range graduation year is rejected."""
    h = auth_headers(users[UserRole.STUDENT])
    resp = client.put("/api/v1/students/me", headers=h, json={"graduation_year": 1900})
    assert resp.status_code == 422


def test_department_other_college_inactive_missing(
    client: TestClient, db: Session, college: College, other_college: College,
    users: dict[UserRole, User], auth_headers: Headers,
) -> None:
    """Departments from another college, inactive or missing are rejected."""
    h = auth_headers(users[UserRole.STUDENT])
    foreign = _dept(db, other_college, "EE")
    inactive = _dept(db, college, "OLD", active=False)
    for dept_id in (foreign.id, inactive.id, 9999):
        resp = client.put("/api/v1/students/me", headers=h, json={"department_id": dept_id})
        assert resp.status_code == 404


def test_roll_number_conflict_same_college_only(
    client: TestClient, db: Session, college: College, other_college: College,
    users: dict[UserRole, User], make_user: MakeUser, auth_headers: Headers,
) -> None:
    """Duplicate roll number in a college is 409; the same in another college is fine."""
    h1 = auth_headers(users[UserRole.STUDENT])
    s2 = make_user(college, UserRole.STUDENT, email="s2@example.com")
    s_other = make_user(other_college, UserRole.STUDENT, email="s3@example.com")
    for _ in range(2):  # re-saving own roll number is not a conflict
        resp = client.put("/api/v1/students/me", headers=h1, json={"roll_number": "R1"})
        assert resp.status_code == 200
    assert client.put("/api/v1/students/me", headers=auth_headers(s2),
                      json={"roll_number": "R1"}).status_code == 409
    assert client.put("/api/v1/students/me", headers=auth_headers(s_other),
                      json={"roll_number": "R1"}).status_code == 200


# ---- academic records -------------------------------------------------------------------


def test_academic_record_crud_and_duplicates(
    client: TestClient, db: Session, users: dict[UserRole, User], auth_headers: Headers
) -> None:
    """Create, list, update, duplicate semester conflicts."""
    h = auth_headers(users[UserRole.STUDENT])
    r = client.post("/api/v1/students/me/academic-records", headers=h,
                    json={"semester": 1, "cgpa": 8.5, "active_arrears": 1, "attendance_pct": 90})
    assert r.status_code == 201
    rid = r.json()["id"]
    assert r.json()["cgpa"] == 8.5
    assert client.post("/api/v1/students/me/academic-records", headers=h,
                       json={"semester": 1, "cgpa": 7}).status_code == 409
    r2 = client.post("/api/v1/students/me/academic-records", headers=h,
                     json={"semester": 2, "cgpa": 7})
    assert r2.status_code == 201
    upd = client.put(f"/api/v1/students/me/academic-records/{rid}", headers=h,
                     json={"cgpa": 9.0, "attendance_pct": None})
    assert upd.status_code == 200
    assert upd.json()["cgpa"] == 9.0
    assert upd.json()["attendance_pct"] is None
    assert client.put(f"/api/v1/students/me/academic-records/{rid}", headers=h,
                      json={"semester": 2}).status_code == 409
    assert client.put(f"/api/v1/students/me/academic-records/{rid}", headers=h,
                      json={"semester": 3}).status_code == 200
    assert client.put("/api/v1/students/me/academic-records/9999", headers=h,
                      json={"cgpa": 1}).status_code == 404
    listing = client.get("/api/v1/students/me/academic-records", headers=h).json()
    assert [x["semester"] for x in listing] == [2, 3]
    assert {"ACADEMIC_RECORD_CREATE", "ACADEMIC_RECORD_UPDATE"} <= set(_actions(db))


@pytest.mark.parametrize(
    "payload",
    [
        {"semester": 0, "cgpa": 5},
        {"semester": 13, "cgpa": 5},
        {"semester": 1, "cgpa": 10.5},
        {"semester": 1, "cgpa": -1},
        {"semester": 1, "cgpa": 5, "active_arrears": -1},
        {"semester": 1, "cgpa": 5, "attendance_pct": 101},
        {"semester": 1, "cgpa": 5, "attendance_pct": -1},
    ],
)
def test_academic_record_bounds(
    client: TestClient, users: dict[UserRole, User], auth_headers: Headers,
    payload: dict[str, Any],
) -> None:
    """Out-of-range values are rejected with 422."""
    resp = client.post("/api/v1/students/me/academic-records",
                       headers=auth_headers(users[UserRole.STUDENT]), json=payload)
    assert resp.status_code == 422


def test_cannot_touch_other_students_rows(
    client: TestClient, college: College, users: dict[UserRole, User], make_user: MakeUser,
    auth_headers: Headers,
) -> None:
    """Another student's record/project/cert ids yield 404."""
    h1 = auth_headers(users[UserRole.STUDENT])
    h2 = auth_headers(make_user(college, UserRole.STUDENT, email="s2@example.com"))
    rid = client.post("/api/v1/students/me/academic-records", headers=h1,
                      json={"semester": 1, "cgpa": 5}).json()["id"]
    pid = client.post("/api/v1/students/me/projects", headers=h1, json={"title": "P"}).json()["id"]
    cid = client.post("/api/v1/students/me/certifications", headers=h1,
                      json={"name": "C"}).json()["id"]
    assert client.put(f"/api/v1/students/me/academic-records/{rid}", headers=h2,
                      json={"cgpa": 1}).status_code == 404
    assert client.delete(f"/api/v1/students/me/projects/{pid}", headers=h2).status_code == 404
    assert client.delete(f"/api/v1/students/me/certifications/{cid}", headers=h2).status_code == 404
    assert client.get("/api/v1/students/me/projects", headers=h2).json() == []
    assert client.get("/api/v1/students/me/certifications", headers=h2).json() == []
    assert client.get("/api/v1/students/me/academic-records", headers=h2).json() == []


# ---- projects / certifications ----------------------------------------------------------


def test_projects_and_certifications_crud(
    client: TestClient, db: Session, users: dict[UserRole, User], auth_headers: Headers
) -> None:
    """Create/list/delete for projects and certifications."""
    h = auth_headers(users[UserRole.STUDENT])
    p = client.post("/api/v1/students/me/projects", headers=h,
                    json={"title": "App", "skills": ["python", "sql"], "url": "https://x.io"})
    assert p.status_code == 201
    assert p.json()["skills"] == ["python", "sql"]
    assert len(client.get("/api/v1/students/me/projects", headers=h).json()) == 1
    assert client.delete(f"/api/v1/students/me/projects/{p.json()['id']}",
                         headers=h).status_code == 204
    assert client.get("/api/v1/students/me/projects", headers=h).json() == []
    c = client.post("/api/v1/students/me/certifications", headers=h,
                    json={"name": "AWS", "issuer": "Amazon", "issued_on": "2025-01-31"})
    assert c.status_code == 201
    assert c.json()["issued_on"] == "2025-01-31"
    assert len(client.get("/api/v1/students/me/certifications", headers=h).json()) == 1
    assert client.delete(f"/api/v1/students/me/certifications/{c.json()['id']}",
                         headers=h).status_code == 204
    assert {"PROJECT_CREATE", "PROJECT_DELETE", "CERTIFICATION_CREATE",
            "CERTIFICATION_DELETE"} <= set(_actions(db))


def test_project_title_required(
    client: TestClient, users: dict[UserRole, User], auth_headers: Headers
) -> None:
    """Empty title is rejected."""
    resp = client.post("/api/v1/students/me/projects",
                       headers=auth_headers(users[UserRole.STUDENT]), json={"title": ""})
    assert resp.status_code == 422


# ---- GET /students/{id} -----------------------------------------------------------------


def test_student_reads_own_but_not_others(
    client: TestClient, db: Session, college: College, users: dict[UserRole, User],
    make_user: MakeUser, auth_headers: Headers,
) -> None:
    """A student sees own detail; another student's id is 404."""
    h = auth_headers(users[UserRole.STUDENT])
    me = client.get("/api/v1/students/me", headers=h).json()
    client.post("/api/v1/students/me/projects", headers=h, json={"title": "P"})
    detail = client.get(f"/api/v1/students/{me['id']}", headers=h)
    assert detail.status_code == 200
    assert len(detail.json()["projects"]) == 1
    other = _student_row(db, make_user(college, UserRole.STUDENT, email="s2@example.com"))
    assert client.get(f"/api/v1/students/{other.id}", headers=h).status_code == 404
    assert "STUDENT_RECORD_READ" not in _actions(db)


def test_faculty_sees_only_assigned(
    client: TestClient, db: Session, college: College, users: dict[UserRole, User],
    make_user: MakeUser, auth_headers: Headers,
) -> None:
    """Faculty reads assigned students only, and the read is audited."""
    assigned = _student_row(db, users[UserRole.STUDENT])
    other = _student_row(db, make_user(college, UserRole.STUDENT, email="s2@example.com"))
    faculty = users[UserRole.FACULTY]
    db.add(FacultyAssignment(college_id=college.id, faculty_user_id=faculty.id,
                             student_id=assigned.id))
    db.commit()
    h = auth_headers(faculty)
    assert client.get(f"/api/v1/students/{assigned.id}", headers=h).status_code == 200
    assert client.get(f"/api/v1/students/{other.id}", headers=h).status_code == 404
    assert "STUDENT_RECORD_READ" in _actions(db)


@pytest.mark.parametrize("role", [UserRole.TPO, UserRole.ADMIN])
def test_tpo_admin_same_college_only(
    client: TestClient, db: Session, college: College, other_college: College,
    users: dict[UserRole, User], make_user: MakeUser, auth_headers: Headers, role: UserRole,
) -> None:
    """TPO/ADMIN read any same-college student, never another college's."""
    own = _student_row(db, users[UserRole.STUDENT])
    foreign = _student_row(db, make_user(other_college, UserRole.STUDENT, email="f@example.com"))
    h = auth_headers(users[role])
    assert client.get(f"/api/v1/students/{own.id}", headers=h).status_code == 200
    assert client.get(f"/api/v1/students/{foreign.id}", headers=h).status_code == 404
    assert client.get("/api/v1/students/9999", headers=h).status_code == 404


def test_hod_and_super_admin_denied(
    client: TestClient, db: Session, users: dict[UserRole, User], auth_headers: Headers
) -> None:
    """HOD and SUPER_ADMIN are denied until a mapping/policy exists."""
    row = _student_row(db, users[UserRole.STUDENT])
    for role in (UserRole.HOD, UserRole.SUPER_ADMIN):
        resp = client.get(f"/api/v1/students/{row.id}", headers=auth_headers(users[role]))
        assert resp.status_code == 403


# ---- admin ------------------------------------------------------------------------------


def test_admin_department_endpoints(
    client: TestClient, db: Session, other_college: College, users: dict[UserRole, User],
    auth_headers: Headers,
) -> None:
    """Admin creates/updates departments in own college; others are forbidden."""
    h = auth_headers(users[UserRole.ADMIN])
    created = client.post("/api/v1/admin/departments", headers=h,
                          json={"name": "Computer Science", "code": "cs"})
    assert created.status_code == 201
    assert created.json()["code"] == "CS"
    dep_id = created.json()["id"]
    assert client.post("/api/v1/admin/departments", headers=h,
                       json={"name": "Dup", "code": "CS"}).status_code == 409
    other = client.post("/api/v1/admin/departments", headers=h, json={"name": "EE", "code": "EE"})
    assert client.put(f"/api/v1/admin/departments/{other.json()['id']}", headers=h,
                      json={"code": "CS"}).status_code == 409
    upd = client.put(f"/api/v1/admin/departments/{dep_id}", headers=h,
                     json={"name": "CSE", "code": "CSE", "is_active": False})
    assert upd.status_code == 200
    assert upd.json()["is_active"] is False
    foreign = _dept(db, other_college, "ZZ")
    assert client.put(f"/api/v1/admin/departments/{foreign.id}", headers=h,
                      json={"name": "x"}).status_code == 404
    for role in (UserRole.STUDENT, UserRole.FACULTY, UserRole.TPO, UserRole.HOD):
        assert client.post("/api/v1/admin/departments", headers=auth_headers(users[role]),
                           json={"name": "N", "code": "N"}).status_code == 403
        assert client.put(f"/api/v1/admin/departments/{dep_id}", headers=auth_headers(users[role]),
                          json={"name": "N"}).status_code == 403
    assert {"DEPARTMENT_CREATE", "DEPARTMENT_UPDATE"} <= set(_actions(db))


def test_admin_faculty_assignments(
    client: TestClient, db: Session, college: College, other_college: College,
    users: dict[UserRole, User], make_user: MakeUser, auth_headers: Headers,
) -> None:
    """Assignment CRUD with role and tenant validation."""
    h = auth_headers(users[UserRole.ADMIN])
    student = _student_row(db, users[UserRole.STUDENT])
    foreign_student = _student_row(
        db, make_user(other_college, UserRole.STUDENT, email="fs@example.com"))
    foreign_faculty = make_user(other_college, UserRole.FACULTY, email="ff@example.com")
    faculty = users[UserRole.FACULTY]
    ok = client.post("/api/v1/admin/faculty-assignments", headers=h,
                     json={"faculty_user_id": faculty.id, "student_id": student.id})
    assert ok.status_code == 201
    assert client.post("/api/v1/admin/faculty-assignments", headers=h,
                       json={"faculty_user_id": faculty.id, "student_id": student.id}
                       ).status_code == 409
    bad_payloads = [
        {"faculty_user_id": users[UserRole.TPO].id, "student_id": student.id},
        {"faculty_user_id": foreign_faculty.id, "student_id": student.id},
        {"faculty_user_id": faculty.id, "student_id": foreign_student.id},
    ]
    for payload in bad_payloads:
        assert client.post("/api/v1/admin/faculty-assignments", headers=h,
                           json=payload).status_code == 404
    assert len(client.get("/api/v1/admin/faculty-assignments", headers=h).json()) == 1
    # Foreign admin sees nothing and cannot delete.
    foreign_admin = make_user(other_college, UserRole.ADMIN, email="fa@example.com")
    fh = auth_headers(foreign_admin)
    assert client.get("/api/v1/admin/faculty-assignments", headers=fh).json() == []
    aid = ok.json()["id"]
    assert client.delete(f"/api/v1/admin/faculty-assignments/{aid}", headers=fh).status_code == 404
    for role in (UserRole.STUDENT, UserRole.FACULTY, UserRole.TPO, UserRole.HOD):
        rh = auth_headers(users[role])
        assert client.get("/api/v1/admin/faculty-assignments", headers=rh).status_code == 403
        assert client.delete(f"/api/v1/admin/faculty-assignments/{aid}",
                             headers=rh).status_code == 403
    assert client.delete(f"/api/v1/admin/faculty-assignments/{aid}", headers=h).status_code == 204
    assert client.delete(f"/api/v1/admin/faculty-assignments/{aid}", headers=h).status_code == 404
    assert {"FACULTY_ASSIGNMENT_CREATE", "FACULTY_ASSIGNMENT_DELETE"} <= set(_actions(db))


# ---- seed script ------------------------------------------------------------------------


def test_parse_departments() -> None:
    """Department spec parsing."""
    assert seed_college.parse_departments(None) == []
    assert seed_college.parse_departments("Computer Science:cs, Mech:ME,") == [
        ("Computer Science", "CS"), ("Mech", "ME")]
    with pytest.raises(ValueError):
        seed_college.parse_departments("nocode")


def test_seed_is_idempotent(db: Session, caplog: pytest.LogCaptureFixture) -> None:
    """Running seed twice creates one college, admin and department set."""
    caplog.set_level(logging.INFO)
    for _ in range(2):
        seed_college.seed(db, "Seed College", "SEED", "Admin@Seed.edu", "Admin", "S3cretPassw0rd",
                          [("Computer Science", "CS")])
    assert len(db.execute(select(College).where(College.code == "SEED")).scalars().all()) == 1
    admins = db.execute(select(User).where(User.email == "admin@seed.edu")).scalars().all()
    assert len(admins) == 1
    assert admins[0].role == UserRole.ADMIN
    assert admins[0].hashed_password != "S3cretPassw0rd"
    assert len(db.execute(select(Department)).scalars().all()) == 1
    assert "S3cretPassw0rd" not in caplog.text


def test_seed_main_password_and_args(
    monkeypatch: pytest.MonkeyPatch, db: Session
) -> None:
    """main() requires ADMIN_PASSWORD, validates departments and uses a session."""
    base = ["--name", "N", "--code", "NC", "--admin-email", "a@n.edu", "--admin-full-name", "A"]
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    assert seed_college.main(base) == 1
    monkeypatch.setenv("ADMIN_PASSWORD", "S3cretPassw0rd")
    assert seed_college.main([*base, "--departments", "bad"]) == 2

    class _Ctx:
        def __enter__(self) -> Session:
            return db

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(seed_college, "SessionLocal", lambda: _Ctx())
    assert seed_college.main([*base, "--departments", "CS:CS"]) == 0
    assert db.execute(select(College).where(College.code == "NC")).scalar_one_or_none() is not None
