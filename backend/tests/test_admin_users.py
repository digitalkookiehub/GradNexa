"""Admin Users and students screen: directory, filters, role changes and their safety rules."""
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    College,
    Department,
    FacultyAssignment,
    HodAssignment,
    Student,
    User,
    UserRole,
)

API = "/api/v1/admin/users"
Headers = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


def make_student(db: Session, user: User, department: Department | None, roll: str | None, year: int | None) -> Student:
    row = Student(
        user_id=user.id,
        college_id=user.college_id,
        department_id=department.id if department else None,
        roll_number=roll,
        graduation_year=year,
    )
    db.add(row)
    db.commit()
    return row


@pytest.fixture
def dept(db: Session, college: College) -> Department:
    d = Department(college_id=college.id, name="Computer Science", code="CSE")
    db.add(d)
    db.commit()
    return d


@pytest.fixture
def other_dept(db: Session, college: College) -> Department:
    d = Department(college_id=college.id, name="Mechanical", code="MECH")
    db.add(d)
    db.commit()
    return d


def test_only_admin_can_use_it(
    client: TestClient, users: dict[UserRole, User], auth_headers: Headers
) -> None:
    for role in (UserRole.STUDENT, UserRole.FACULTY, UserRole.TPO, UserRole.HOD, UserRole.SUPER_ADMIN):
        assert client.get(API, headers=auth_headers(users[role])).status_code == 403
        assert (
            client.put(f"{API}/{users[UserRole.STUDENT].id}/role", json={"role": "FACULTY"}, headers=auth_headers(users[role])).status_code
            == 403
        )
    assert client.get(API).status_code == 401


def test_list_is_scoped_to_the_admins_college(
    client: TestClient, college: College, other_college: College, make_user: MakeUser, auth_headers: Headers
) -> None:
    admin = make_user(college, UserRole.ADMIN, "admin@a.com")
    make_user(college, UserRole.STUDENT, "stu@a.com")
    make_user(other_college, UserRole.STUDENT, "stu@b.com")
    body = client.get(API, headers=auth_headers(admin)).json()
    emails = {i["email"] for i in body["items"]}
    assert emails == {"admin@a.com", "stu@a.com"}
    assert body["total"] == 2
    assert "hashed_password" not in client.get(API, headers=auth_headers(admin)).text


def test_student_columns_and_profile_status(
    client: TestClient, db: Session, college: College, dept: Department, make_user: MakeUser, auth_headers: Headers
) -> None:
    admin = make_user(college, UserRole.ADMIN, "admin@a.com")
    done = make_user(college, UserRole.STUDENT, "done@a.com")
    partial = make_user(college, UserRole.STUDENT, "partial@a.com")
    make_student(db, done, dept, "R001", 2026)
    make_student(db, partial, None, None, None)
    items = {i["email"]: i for i in client.get(API, headers=auth_headers(admin)).json()["items"]}
    s = items["done@a.com"]["student"]
    assert s["department_name"] == "Computer Science" and s["roll_number"] == "R001" and s["profile_complete"] is True
    assert items["partial@a.com"]["student"]["profile_complete"] is False
    assert items["admin@a.com"]["student"] is None


def test_search_role_and_department_filters(
    client: TestClient, db: Session, college: College, dept: Department, other_dept: Department,
    make_user: MakeUser, auth_headers: Headers,
) -> None:
    admin = make_user(college, UserRole.ADMIN, "admin@a.com")
    asha = make_user(college, UserRole.STUDENT, "asha@a.com")
    asha.full_name = "Asha Rao"
    ravi = make_user(college, UserRole.STUDENT, "ravi@a.com")
    ravi.full_name = "Ravi Kumar"
    make_user(college, UserRole.FACULTY, "prof@a.com")
    db.commit()
    make_student(db, asha, dept, "CSE-101", 2026)
    make_student(db, ravi, other_dept, "MEC-202", 2027)
    h = auth_headers(admin)

    def emails(**params: object) -> set[str]:
        return {i["email"] for i in client.get(API, params=params, headers=h).json()["items"]}

    assert emails(search="asha") == {"asha@a.com"}
    assert emails(search="RAVI KUMAR") == {"ravi@a.com"}
    assert emails(search="mec-202") == {"ravi@a.com"}
    assert emails(search="@a.com") == {"admin@a.com", "asha@a.com", "ravi@a.com", "prof@a.com"}
    assert emails(role="FACULTY") == {"prof@a.com"}
    assert emails(role="STUDENT", department_id=dept.id) == {"asha@a.com"}
    assert emails(search="100%") == set()
    assert emails(search="_") == set()


def test_pagination(client: TestClient, college: College, make_user: MakeUser, auth_headers: Headers) -> None:
    admin = make_user(college, UserRole.ADMIN, "admin@a.com")
    for n in range(5):
        make_user(college, UserRole.STUDENT, f"s{n}@a.com")
    h = auth_headers(admin)
    first = client.get(API, params={"page": 1, "page_size": 4}, headers=h).json()
    second = client.get(API, params={"page": 2, "page_size": 4}, headers=h).json()
    assert first["total"] == 6 and len(first["items"]) == 4 and len(second["items"]) == 2
    assert not {i["id"] for i in first["items"]} & {i["id"] for i in second["items"]}
    assert client.get(API, params={"page_size": 101}, headers=h).status_code == 422
    assert client.get(API, params={"page": 0}, headers=h).status_code == 422


def test_role_change_applies_immediately_and_is_audited(
    client: TestClient, db: Session, college: College, make_user: MakeUser, auth_headers: Headers
) -> None:
    admin = make_user(college, UserRole.ADMIN, "admin@a.com")
    person = make_user(college, UserRole.STUDENT, "person@a.com")
    old_token_headers = auth_headers(person)
    assert client.get("/api/v1/dashboard/faculty", headers=old_token_headers).status_code == 403
    res = client.put(f"{API}/{person.id}/role", json={"role": "FACULTY"}, headers=auth_headers(admin))
    assert res.status_code == 200
    assert res.json()["role"] == "FACULTY" and res.json()["previous_role"] == "STUDENT"
    # the same, already-issued token now has faculty access because the role is read from the database
    assert client.get("/api/v1/dashboard/faculty", headers=old_token_headers).status_code == 200
    log = db.execute(select(AuditLog).where(AuditLog.action == "USER_ROLE_CHANGE")).scalar_one()
    assert log.user_id == admin.id and log.resource_id == str(person.id)
    assert log.metadata_json == {"from": "STUDENT", "to": "FACULTY", "removed_faculty_assignments": 0, "removed_hod_assignments": 0}


def test_same_role_is_a_no_op(client: TestClient, db: Session, college: College, make_user: MakeUser, auth_headers: Headers) -> None:
    admin = make_user(college, UserRole.ADMIN, "admin@a.com")
    person = make_user(college, UserRole.TPO, "tpo@a.com")
    assert client.put(f"{API}/{person.id}/role", json={"role": "TPO"}, headers=auth_headers(admin)).status_code == 200
    assert db.execute(select(AuditLog).where(AuditLog.action == "USER_ROLE_CHANGE")).first() is None


def test_cannot_change_your_own_role(client: TestClient, college: College, make_user: MakeUser, auth_headers: Headers) -> None:
    admin = make_user(college, UserRole.ADMIN, "admin@a.com")
    res = client.put(f"{API}/{admin.id}/role", json={"role": "STUDENT"}, headers=auth_headers(admin))
    assert res.status_code == 409
    assert res.json()["detail"] == "You cannot change your own role"


def test_super_admin_is_neither_assignable_nor_changeable(
    client: TestClient, college: College, make_user: MakeUser, auth_headers: Headers
) -> None:
    admin = make_user(college, UserRole.ADMIN, "admin@a.com")
    boss = make_user(college, UserRole.SUPER_ADMIN, "boss@a.com")
    person = make_user(college, UserRole.STUDENT, "p@a.com")
    h = auth_headers(admin)
    assert client.put(f"{API}/{person.id}/role", json={"role": "SUPER_ADMIN"}, headers=h).status_code == 422
    assert client.put(f"{API}/{boss.id}/role", json={"role": "STUDENT"}, headers=h).status_code == 403
    assert client.put(f"{API}/{person.id}/role", json={"role": "NOPE"}, headers=h).status_code == 422


def test_cannot_touch_another_colleges_user(
    client: TestClient, college: College, other_college: College, make_user: MakeUser, auth_headers: Headers
) -> None:
    admin = make_user(college, UserRole.ADMIN, "admin@a.com")
    outsider = make_user(other_college, UserRole.STUDENT, "out@b.com")
    assert client.put(f"{API}/{outsider.id}/role", json={"role": "FACULTY"}, headers=auth_headers(admin)).status_code == 404
    assert client.put(f"{API}/999999/role", json={"role": "FACULTY"}, headers=auth_headers(admin)).status_code == 404


def test_leaving_faculty_or_hod_removes_their_assignments(
    client: TestClient, db: Session, college: College, dept: Department, make_user: MakeUser, auth_headers: Headers
) -> None:
    admin = make_user(college, UserRole.ADMIN, "admin@a.com")
    faculty = make_user(college, UserRole.FACULTY, "f@a.com")
    hod = make_user(college, UserRole.HOD, "h@a.com")
    stu = make_user(college, UserRole.STUDENT, "s@a.com")
    student = make_student(db, stu, dept, "R1", 2026)
    db.add(FacultyAssignment(college_id=college.id, faculty_user_id=faculty.id, student_id=student.id))
    db.add(HodAssignment(college_id=college.id, hod_user_id=hod.id, department_id=dept.id))
    db.commit()
    h = auth_headers(admin)
    r1 = client.put(f"{API}/{faculty.id}/role", json={"role": "STUDENT"}, headers=h).json()
    r2 = client.put(f"{API}/{hod.id}/role", json={"role": "TPO"}, headers=h).json()
    assert r1["removed_faculty_assignments"] == 1 and r2["removed_hod_assignments"] == 1
    assert db.execute(select(FacultyAssignment)).first() is None
    assert db.execute(select(HodAssignment)).first() is None


def test_faculty_assignment_list_includes_names(
    client: TestClient, db: Session, college: College, dept: Department, make_user: MakeUser, auth_headers: Headers
) -> None:
    admin = make_user(college, UserRole.ADMIN, "admin@a.com")
    faculty = make_user(college, UserRole.FACULTY, "f@a.com")
    stu = make_user(college, UserRole.STUDENT, "s@a.com")
    student = make_student(db, stu, dept, "R1", 2026)
    h = auth_headers(admin)
    created = client.post("/api/v1/admin/faculty-assignments", json={"faculty_user_id": faculty.id, "student_id": student.id}, headers=h)
    assert created.status_code == 201
    rows = client.get("/api/v1/admin/faculty-assignments", headers=h).json()
    assert rows == [
        {
            "id": created.json()["id"],
            "faculty_user_id": faculty.id,
            "faculty_name": faculty.full_name,
            "faculty_email": "f@a.com",
            "student_id": student.id,
            "student_name": stu.full_name,
            "student_email": "s@a.com",
        }
    ]
