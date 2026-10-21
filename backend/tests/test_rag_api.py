"""API tests: upload validation, approval workflow, scoping, isolation, roles, audit."""
import io
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    AuditLog,
    College,
    Department,
    RAGChunk,
    RAGDocument,
    Student,
    User,
    UserRole,
)
from tests.test_resume_api import blank_pdf, make_docx, make_pdf

API = "/api/v1/admin/knowledge-documents"
SEARCH = "/api/v1/knowledge/search"
NO_INFO = "I don't have enough approved information to answer this confidently."
TEXT = (
    b"# Placement Policy\n\nStudents need a minimum CGPA of 6.5 to be eligible for "
    b"campus placement drives.\n\n# Offers\n\nThe one offer policy allows a dream offer only."
)


class Env:
    def __init__(
        self, client: TestClient, db: Session, h: Callable[[User], dict[str, str]],
        make_user: Callable[..., User], a: College, b: College, tmp: Path,
    ) -> None:
        self.client, self.db, self.h, self.a, self.b, self.tmp = client, db, h, a, b, tmp
        self.admin = make_user(a, UserRole.ADMIN)
        self.faculty = make_user(a, UserRole.FACULTY)
        self.student = make_user(a, UserRole.STUDENT)
        self.student2 = make_user(a, UserRole.STUDENT, email="s2@a.example.com")
        self.hod = make_user(a, UserRole.HOD)
        self.admin_b = make_user(b, UserRole.ADMIN)
        self.student_b = make_user(b, UserRole.STUDENT)

    def req(self, method: str, path: str, user: User, **kw: Any) -> Any:
        return self.client.request(method, path, headers=self.h(user), **kw)

    def upload(
        self, user: User, data: bytes = TEXT, name: str = "policy.md", title: str = "Policy",
        source_type: str = "POLICY", dept: int | None = None,
    ) -> Any:
        form: dict[str, str] = {"title": title, "source_type": source_type}
        if dept is not None:
            form["department_id"] = str(dept)
        return self.req("POST", API, user, files={"file": (name, io.BytesIO(data))}, data=form)

    def approved(self, user: User | None = None, **kw: Any) -> dict[str, Any]:
        r = self.upload(user or self.admin, **kw)
        assert r.status_code == 201, r.text
        a = self.req("POST", f"{API}/{r.json()['id']}/approve", self.admin if user is None
                     or user.college_id == self.a.id else self.admin_b)
        assert a.status_code == 200, a.text
        return dict(a.json())

    def search(self, user: User, q: str = "minimum CGPA placement eligibility") -> Any:
        return self.req("POST", SEARCH, user, json={"query": q})

    def dept(self, college: College, code: str) -> Department:
        d = Department(college_id=college.id, name=f"Dept {code}", code=code)
        self.db.add(d)
        self.db.commit()
        return d

    def actions(self) -> list[str]:
        return list(self.db.execute(select(AuditLog.action)).scalars())


@pytest.fixture
def env(
    client: TestClient, db: Session, auth_headers: Callable[[User], dict[str, str]],
    make_user: Callable[..., User], college: College, other_college: College,
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> Env:
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 1)
    return Env(client, db, auth_headers, make_user, college, other_college, tmp_path / "uploads")


# ------------------------------------------------------------------ upload validation


def test_upload_text_pdf_docx_ok(env: Env) -> None:
    for data, name in (
        (TEXT, "a.txt"),
        (make_pdf(["SQL joins combine rows from tables."]), "a.pdf"),
        (make_docx(["Binary trees store ordered keys."]), "a.docx"),
    ):
        r = env.upload(env.faculty, data=data, name=name)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["status"] == "PENDING" and body["chunk_count"] >= 1
        assert body["approved_by"] is None and body["department_name"] is None
        assert "storage_key" not in body


def test_upload_markdown_content_type(env: Env) -> None:
    assert env.upload(env.admin, name="n.md").json()["content_type"] == "text/markdown"
    assert env.upload(env.admin, name="n.txt").json()["content_type"] == "text/plain"


def test_upload_wrong_type_415(env: Env) -> None:
    assert env.upload(env.admin, data=b"\x89PNG\r\n\x1a\n\x00\x00", name="x.png").status_code == 415
    assert env.upload(env.admin, data=b"abc\x00def", name="x.txt").status_code == 415
    assert env.upload(env.admin, data=b"\xff\xfe\xfa bad", name="x.txt").status_code == 415


def test_upload_pretends_pdf_by_extension_is_judged_by_content(env: Env) -> None:
    r = env.upload(env.admin, data=b"%PDF-1.4 garbage", name="a.pdf")
    assert r.status_code == 422


def test_upload_oversize_413(env: Env) -> None:
    r = env.upload(env.admin, data=b"a " * (1024 * 1024 + 10), name="big.txt")
    assert r.status_code == 413


def test_upload_empty_and_blank_422(env: Env) -> None:
    assert env.upload(env.admin, data=b"", name="e.txt").status_code == 422
    assert env.upload(env.admin, data=b"  \n \n", name="e.txt").status_code == 422


def test_upload_corrupt_docx_and_zip_422(env: Env) -> None:
    assert env.upload(env.admin, data=b"PK\x03\x04junk", name="a.docx").status_code in (415, 422)


def test_upload_scanned_pdf_422_message(env: Env) -> None:
    r = env.upload(env.admin, data=blank_pdf(), name="scan.pdf")
    assert r.status_code == 422
    assert r.json()["detail"] == "No extractable text found (OCR is not implemented in this phase)"
    assert not list(env.tmp.rglob("*")) or not any(p.is_file() for p in env.tmp.rglob("*"))


def test_upload_bad_department_404_and_bad_source_422(env: Env) -> None:
    other = env.dept(env.b, "XX")
    assert env.upload(env.admin, dept=other.id).status_code == 404
    assert env.upload(env.admin, source_type="NOPE").status_code == 422


# ------------------------------------------------------------------ roles


def test_role_guards(env: Env) -> None:
    assert env.upload(env.student).status_code == 403
    assert env.upload(env.hod).status_code == 403
    doc = env.upload(env.faculty).json()
    assert env.req("POST", f"{API}/{doc['id']}/approve", env.faculty).status_code == 403
    assert env.req("POST", f"{API}/{doc['id']}/archive", env.faculty).status_code == 403
    assert env.req("GET", API, env.student).status_code == 403
    assert env.req("GET", API, env.faculty).status_code == 200
    assert env.req("DELETE", f"{API}/{doc['id']}", env.faculty).status_code == 204
    assert env.client.post(SEARCH, json={"query": "x"}).status_code == 401


# ------------------------------------------------------------------ workflow


def test_approval_workflow_and_retrievability(env: Env) -> None:
    doc = env.upload(env.admin).json()
    assert env.search(env.student).json()["insufficient_evidence"] is True
    a = env.req("POST", f"{API}/{doc['id']}/approve", env.admin).json()
    assert a["status"] == "APPROVED" and a["approved_by"] == env.admin.id and a["approved_at"]
    res = env.search(env.student).json()
    assert res["insufficient_evidence"] is False and res["message"] is None
    assert res["passages"][0]["document_id"] == doc["id"]
    arch = env.req("POST", f"{API}/{doc['id']}/archive", env.admin).json()
    assert arch["status"] == "ARCHIVED"
    assert env.search(env.student).json()["insufficient_evidence"] is True
    assert env.req("POST", f"{API}/{doc['id']}/approve", env.admin).json()["status"] == "APPROVED"
    assert env.search(env.student).json()["passages"]
    pend = env.upload(env.admin).json()
    assert env.req("POST", f"{API}/{pend['id']}/archive", env.admin).json()["status"] == "ARCHIVED"


def test_insufficient_evidence_exact_message(env: Env) -> None:
    env.approved()
    r = env.search(env.student, "volcano weather in antarctica").json()
    assert r == {"query": "volcano weather in antarctica", "insufficient_evidence": True,
                 "message": NO_INFO, "passages": []}


def test_list_filters_get_chunks_and_update(env: Env) -> None:
    d1 = env.upload(env.admin, title="One").json()
    env.upload(env.admin, title="Two", source_type="SYLLABUS")
    env.req("POST", f"{API}/{d1['id']}/approve", env.admin)
    assert len(env.req("GET", API, env.faculty).json()) == 2
    assert len(env.req("GET", f"{API}?status=APPROVED", env.faculty).json()) == 1
    assert env.req("GET", f"{API}?source_type=SYLLABUS", env.faculty).json()[0]["title"] == "Two"
    assert env.req("GET", f"{API}/{d1['id']}", env.faculty).json()["title"] == "One"
    ch = env.req("GET", f"{API}/{d1['id']}/chunks?limit=1&offset=0", env.faculty).json()
    assert ch["total"] == d1["chunk_count"] and len(ch["chunks"]) == 1
    assert set(ch["chunks"][0]) == {"id", "chunk_index", "content", "heading"}
    assert env.req("GET", f"{API}/999999", env.admin).status_code == 404
    dept = env.dept(env.a, "CS")
    u = env.req("PUT", f"{API}/{d1['id']}", env.faculty,
                json={"title": " New ", "source_type": "OTHER", "department_id": dept.id}).json()
    assert u["title"] == "New" and u["department_name"] == "Dept CS"
    assert u["source_type"] == "OTHER" and u["status"] == "APPROVED"
    cleared = env.req("PUT", f"{API}/{d1['id']}", env.faculty, json={"department_id": None}).json()
    assert cleared["department_id"] is None and cleared["title"] == "New"
    assert env.req("PUT", f"{API}/{d1['id']}", env.admin, json={"title": " "}).status_code == 422
    other = env.dept(env.b, "ZZ")
    assert env.req("PUT", f"{API}/{d1['id']}", env.admin,
                   json={"department_id": other.id}).status_code == 404


def test_delete_removes_chunks_and_file(env: Env) -> None:
    doc = env.approved()
    row = env.db.get(RAGDocument, doc["id"])
    assert row is not None
    path = env.tmp / row.storage_key
    assert path.is_file()
    assert env.req("DELETE", f"{API}/{doc['id']}", env.admin).status_code == 204
    assert not path.exists()
    env.db.expire_all()
    assert env.db.get(RAGDocument, doc["id"]) is None
    assert env.db.execute(select(RAGChunk.id)).first() is None
    assert env.req("DELETE", f"{API}/{doc['id']}", env.admin).status_code == 404
    assert env.search(env.student).json()["insufficient_evidence"] is True


# ------------------------------------------------------------------ scoping / isolation


def test_student_department_scoping(env: Env) -> None:
    cs, ec = env.dept(env.a, "CS"), env.dept(env.a, "EC")
    env.db.add(Student(user_id=env.student.id, college_id=env.a.id, department_id=cs.id))
    env.db.add(Student(user_id=env.student2.id, college_id=env.a.id, department_id=ec.id))
    env.db.commit()
    env.approved(title="CS only", dept=cs.id)
    env.approved(title="Everyone")
    titles = lambda u: {p["document_title"] for p in env.search(u, "minimum CGPA placement").json()["passages"]}  # noqa: E731
    assert titles(env.student) == {"CS only", "Everyone"}
    assert titles(env.student2) == {"Everyone"}
    assert titles(env.faculty) == {"CS only", "Everyone"}
    assert titles(env.hod) == {"CS only", "Everyone"}


def test_student_without_department_sees_only_unscoped(env: Env) -> None:
    cs = env.dept(env.a, "CS")
    env.approved(title="CS only", dept=cs.id)
    assert env.search(env.student).json()["insufficient_evidence"] is True
    env.approved(title="Everyone")
    assert {p["document_title"] for p in env.search(env.student).json()["passages"]} == {"Everyone"}


def test_cross_college_isolation(env: Env) -> None:
    doc_a = env.approved(title="A doc")
    doc_b = env.approved(env.admin_b, title="B doc")
    only_a = {p["document_title"] for p in env.search(env.student).json()["passages"]}
    only_b = {p["document_title"] for p in env.search(env.student_b).json()["passages"]}
    assert only_a == {"A doc"} and only_b == {"B doc"}
    for method, suffix in (("GET", ""), ("GET", "/chunks"), ("POST", "/approve"),
                           ("POST", "/archive"), ("DELETE", "")):
        r = env.req(method, f"{API}/{doc_a['id']}{suffix}", env.admin_b)
        assert r.status_code == 404, (method, suffix)
    assert env.req("PUT", f"{API}/{doc_a['id']}", env.admin_b, json={"title": "x"}).status_code == 404
    assert [d["id"] for d in env.req("GET", API, env.admin_b).json()] == [doc_b["id"]]
    assert env.db.get(RAGDocument, doc_a["id"]) is not None


def test_search_validation(env: Env) -> None:
    assert env.req("POST", SEARCH, env.student, json={"query": ""}).status_code == 422
    assert env.req("POST", SEARCH, env.student, json={"query": "x" * 501}).status_code == 422
    assert env.req("POST", SEARCH, env.student, json={"query": "a", "top_k": 11}).status_code == 422
    assert env.req("POST", SEARCH, env.student, json={"query": "a", "top_k": 0}).status_code == 422


def test_top_k_limits_results(env: Env) -> None:
    for i in range(4):
        env.approved(title=f"Doc {i}")
    r = env.req("POST", SEARCH, env.student,
                json={"query": "minimum CGPA placement", "top_k": 2}).json()
    assert len(r["passages"]) == 2


# ------------------------------------------------------------------ audit


def test_audit_rows_without_query_text(env: Env) -> None:
    doc = env.approved()
    q = "super secret minimum CGPA placement query"
    env.search(env.student, q)
    env.req("PUT", f"{API}/{doc['id']}", env.admin, json={"title": "T2"})
    env.req("POST", f"{API}/{doc['id']}/archive", env.admin)
    env.req("DELETE", f"{API}/{doc['id']}", env.admin)
    acts = env.actions()
    for a in ("KNOWLEDGE_UPLOAD", "KNOWLEDGE_APPROVE", "KNOWLEDGE_SEARCH", "KNOWLEDGE_UPDATE",
              "KNOWLEDGE_ARCHIVE", "KNOWLEDGE_DELETE"):
        assert a in acts, a
    row = env.db.execute(
        select(AuditLog).where(AuditLog.action == "KNOWLEDGE_SEARCH")
    ).scalar_one()
    assert row.metadata_json is not None and row.metadata_json["query_length"] == len(q)
    dump = " ".join(str(r.metadata_json) + str(r.resource_id) for r in
                    env.db.execute(select(AuditLog)).scalars())
    assert "secret" not in dump
