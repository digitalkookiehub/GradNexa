"""Resume upload / analysis API tests."""
import io
import os
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import docx
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    AuditLog,
    CareerRole,
    College,
    Department,
    Resume,
    ResumeAnalysis,
    RoleSkill,
    Skill,
    SkillCategory,
    User,
    UserRole,
)
from app.models.company import Company  # noqa: E402
from app.models.job_description import JobDescription, JobStatus  # noqa: E402
from app.models.job_skill import JobSkill  # noqa: E402

API = "/api/v1"
Headers = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]

RESUME_TEXT = [
    "Jane Roe",
    "",
    "Education",
    "B.Tech CSE 2024",
    "",
    "Technical Skills",
    "Python, SQL, C++",
    "",
    "Projects",
    "Built a Python chatbot",
]


def make_pdf(lines: list[str]) -> bytes:
    """Hand-built single-page PDF containing the lines as text."""
    ops = ["BT", "/F1 12 Tf", "14 TL", "50 750 Td"]
    for line in lines:
        esc = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        ops.append(f"({esc}) Tj T*")
    ops.append("ET")
    stream = "\n".join(ops).encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def make_docx(lines: list[str]) -> bytes:
    document = docx.Document()
    for line in lines:
        document.add_paragraph(line)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


def blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def encrypted_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt("secret")
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class Env:
    def __init__(
        self, client: TestClient, db: Session, h: Headers, make_user: MakeUser,
        a: College, b: College, upload_dir: Path,
    ) -> None:
        self.client, self.db, self.h, self.a, self.b = client, db, h, a, b
        self.upload_dir = upload_dir
        self.student = make_user(a, UserRole.STUDENT)
        self.student2 = make_user(a, UserRole.STUDENT, email="s2@a.example.com")
        self.student_b = make_user(b, UserRole.STUDENT)
        self.others = {
            r: make_user(a, r) for r in UserRole if r != UserRole.STUDENT
        }
        cat = SkillCategory(college_id=a.id, name="Tech")
        cat_b = SkillCategory(college_id=b.id, name="Tech")
        db.add_all([cat, cat_b])
        db.commit()
        self.skills: dict[str, Skill] = {}
        for name in ["Python", "SQL", "C++", "Rust", "C"]:
            s = Skill(college_id=a.id, category_id=cat.id, name=name)
            db.add(s)
            self.skills[name] = s
        # same skill name exists in college B and must never leak
        self.b_skill = Skill(college_id=b.id, category_id=cat_b.id, name="Kotlin")
        db.add(self.b_skill)
        db.commit()

    def req(self, method: str, path: str, user: User, **kw: Any) -> Any:
        return self.client.request(method, API + path, headers=self.h(user), **kw)

    def upload(
        self, user: User, data: bytes, name: str = "resume.pdf", ctype: str = "application/pdf"
    ) -> Any:
        return self.req("POST", "/resumes", user, files={"file": (name, data, ctype)})

    def good(self, user: User | None = None) -> dict[str, Any]:
        r = self.upload(user or self.student, make_pdf(RESUME_TEXT))
        assert r.status_code == 201, r.text
        return dict(r.json())

    def role(
        self, name: str = "Backend Dev", college: College | None = None,
        dept: Department | None = None, active: bool = True, with_skills: bool = True,
    ) -> CareerRole:
        c = college or self.a
        role = CareerRole(
            college_id=c.id, name=name, is_active=active,
            department_id=dept.id if dept else None,
        )
        self.db.add(role)
        self.db.commit()
        if with_skills:
            for nm, w in [("Python", 3), ("SQL", 1), ("Rust", 2)]:
                self.db.add(
                    RoleSkill(
                        role_id=role.id, college_id=c.id, skill_id=self.skills[nm].id,
                        required_level=60, weight=w,
                    )
                )
            self.db.commit()
        return role

    def files_on_disk(self) -> list[Path]:
        return [p for p in self.upload_dir.rglob("*") if p.is_file()]


@pytest.fixture
def env(
    client: TestClient, db: Session, auth_headers: Headers, make_user: MakeUser,
    college: College, other_college: College, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> Env:
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 1)
    return Env(client, db, auth_headers, make_user, college, other_college, tmp_path / "uploads")


# ---- upload ---------------------------------------------------------------------------------
def test_upload_pdf(env: Env) -> None:
    body = env.good()
    assert body["content_type"] == "application/pdf"
    assert body["has_text"] is True and body["text_length"] > 10
    assert body["page_count"] == 1 and body["original_filename"] == "resume.pdf"
    assert set(body) == {
        "id", "original_filename", "content_type", "size_bytes", "page_count",
        "uploaded_at", "has_text", "text_length",
    }
    text = env.req("GET", f"/resumes/{body['id']}/text", env.student).json()["text"]
    assert "Python, SQL, C++" in text and len(text) == body["text_length"]
    assert len(env.files_on_disk()) == 1
    assert "RESUME_UPLOAD" in [a for a in env.db.execute(select(AuditLog.action)).scalars()]


def test_upload_docx_ignores_client_content_type(env: Env) -> None:
    r = env.upload(env.student, make_docx(RESUME_TEXT), "cv.bin", "text/plain")
    assert r.status_code == 201, r.text
    assert r.json()["content_type"].endswith("wordprocessingml.document")
    assert r.json()["page_count"] is None and r.json()["has_text"] is True
    text = env.req("GET", f"/resumes/{r.json()['id']}/text", env.student).json()["text"]
    assert "Technical Skills" in text


def test_spoofed_txt_as_pdf_is_415(env: Env) -> None:
    r = env.upload(env.student, b"hello, I am just text", "evil.pdf", "application/pdf")
    assert r.status_code == 415
    assert env.files_on_disk() == []


def test_other_zip_is_415_and_corrupt_zip_is_not_accepted(env: Env) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("hello.txt", "x")
    assert env.upload(env.student, buf.getvalue(), "a.docx").status_code == 415
    # PK header but not a zip
    assert env.upload(env.student, b"PK\x03\x04garbage", "a.docx").status_code == 415


def test_corrupt_docx_422(env: Env) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", "<not-valid")
    r = env.upload(env.student, buf.getvalue(), "a.docx")
    assert r.status_code == 422 and "corrupt" in r.json()["detail"]


def test_zip_bomb_rejected(env: Env) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", b"0" * (60 * 1024 * 1024))
    data = buf.getvalue()
    assert len(data) < 1024 * 1024
    r = env.upload(env.student, data, "bomb.docx")
    assert r.status_code == 422 and "unsafe size" in r.json()["detail"]


def test_oversize_413(env: Env) -> None:
    r = env.upload(env.student, b"%PDF-1.4\n" + b"0" * (1024 * 1024 + 10))
    assert r.status_code == 413
    assert env.files_on_disk() == []


def test_empty_file(env: Env) -> None:
    r = env.upload(env.student, b"")
    assert r.status_code == 422 and "empty" in r.json()["detail"]


def test_missing_file_field_422(env: Env) -> None:
    assert env.req("POST", "/resumes", env.student).status_code == 422


def test_corrupt_pdf_422(env: Env) -> None:
    r = env.upload(env.student, b"%PDF-1.4\nthis is not a real pdf at all")
    assert r.status_code == 422 and "corrupt" in r.json()["detail"]


def test_password_protected_pdf_422(env: Env) -> None:
    r = env.upload(env.student, encrypted_pdf())
    assert r.status_code == 422 and "Password" in r.json()["detail"]


def test_sanitise_filename_unit() -> None:
    from app.services.resume_service import sanitise_filename

    assert sanitise_filename("../../etc/pass\x00wd\r\n.pdf") == "passwd.pdf"
    assert sanitise_filename(None) == "resume" and sanitise_filename("..") == "resume"


def test_filename_sanitised_and_storage_name_random(env: Env) -> None:
    r = env.upload(env.student, make_pdf(RESUME_TEXT), "../../etc/passwd.pdf")
    assert r.status_code == 201
    assert r.json()["original_filename"] == "passwd.pdf"
    r2 = env.upload(env.student, make_pdf(RESUME_TEXT), "C:\\Users\\x\\..\\cv.pdf")
    assert r2.json()["original_filename"] == "cv.pdf"
    r3 = env.upload(env.student, make_pdf(RESUME_TEXT), "a" * 400 + ".pdf")
    assert len(r3.json()["original_filename"]) == 255
    files = env.files_on_disk()
    assert len(files) == 3
    for f in files:
        assert f.parent.name == str(env.a.id)
        assert len(f.name) == 32 and all(c in "0123456789abcdef" for c in f.name)
        assert env.upload_dir.resolve() in f.resolve().parents
    keys = list(env.db.execute(select(Resume.storage_key)).scalars())
    assert len(set(keys)) == 3 and all(k.startswith(f"{env.a.id}/") for k in keys)


def test_scanned_pdf_has_no_text_and_note(env: Env) -> None:
    r = env.upload(env.student, blank_pdf())
    assert r.status_code == 201
    body = r.json()
    assert body["has_text"] is False and body["text_length"] == 0
    assert env.req("GET", f"/resumes/{body['id']}/text", env.student).json() == {"text": ""}
    a = env.req(
        "POST", f"/resumes/{body['id']}/analyze", env.student,
        json={"jd_text": "Python needed"},
    )
    assert a.status_code == 201
    data = a.json()
    assert any("No extractable text found" in n and "OCR" in n for n in data["notes"])
    assert data["extracted"]["skills"] == []
    assert data["jd_match"]["match_percent"] is None


def test_no_download_endpoint(env: Env) -> None:
    rid = env.good()["id"]
    for path in (f"/resumes/{rid}/download", f"/resumes/{rid}/file"):
        assert env.req("GET", path, env.student).status_code in (404, 405)


# ---- list / get / delete ------------------------------------------------------------------
def test_list_get_delete(env: Env) -> None:
    first, second = env.good(), env.good()
    listing = env.req("GET", "/resumes", env.student).json()
    assert [r["id"] for r in listing] == [second["id"], first["id"]]
    assert env.req("GET", f"/resumes/{first['id']}", env.student).json()["id"] == first["id"]
    env.req("POST", f"/resumes/{first['id']}/analyze", env.student, json={})
    assert len(env.files_on_disk()) == 2
    d = env.req("DELETE", f"/resumes/{first['id']}", env.student)
    assert d.status_code == 204 and d.content == b""
    assert len(env.files_on_disk()) == 1
    assert env.req("GET", f"/resumes/{first['id']}", env.student).status_code == 404
    assert env.db.execute(
        select(func.count()).select_from(ResumeAnalysis)
    ).scalar_one() == 0
    actions = list(env.db.execute(select(AuditLog.action)).scalars())
    assert {"RESUME_UPLOAD", "RESUME_ANALYZE", "RESUME_DELETE"} <= set(actions)
    assert env.req("DELETE", f"/resumes/{first['id']}", env.student).status_code == 404


# ---- isolation / guards --------------------------------------------------------------------
def test_cross_student_and_cross_college_isolation(env: Env) -> None:
    rid = env.good()["id"]
    for user in (env.student2, env.student_b):
        assert env.req("GET", "/resumes", user).json() == []
        for method, suffix in [
            ("GET", ""), ("GET", "/text"), ("DELETE", ""), ("POST", "/analyze"),
            ("GET", "/analysis"), ("GET", "/analyses"),
        ]:
            r = env.req(method, f"/resumes/{rid}{suffix}", user, **(
                {"json": {}} if method == "POST" else {}
            ))
            assert r.status_code == 404, (user.email, method, suffix)
    assert len(env.files_on_disk()) == 1
    assert env.req("GET", f"/resumes/{rid}", env.student).status_code == 200


def test_non_students_forbidden(env: Env) -> None:
    rid = env.good()["id"]
    for user in env.others.values():
        assert env.req("GET", "/resumes", user).status_code == 403
        assert env.req("GET", f"/resumes/{rid}", user).status_code == 403
        assert env.req("GET", f"/resumes/{rid}/text", user).status_code == 403
        assert env.req("DELETE", f"/resumes/{rid}", user).status_code == 403
        assert env.upload(user, make_pdf(RESUME_TEXT)).status_code == 403
        assert env.req("POST", f"/resumes/{rid}/analyze", user, json={}).status_code == 403
    assert env.client.get(f"{API}/resumes").status_code == 401


# ---- analysis ------------------------------------------------------------------------------
def test_analyze_basic_and_history(env: Env) -> None:
    rid = env.good()["id"]
    assert env.req("GET", f"/resumes/{rid}/analysis", env.student).status_code == 404
    assert env.req("GET", f"/resumes/{rid}/analyses", env.student).json() == []
    r = env.req("POST", f"/resumes/{rid}/analyze", env.student)  # body-less allowed
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["extractor_version"] == "rules-1" and a["role_id"] is None
    assert a["role_name"] is None and a["role_match"] is None and a["jd_match"] is None
    text = env.req("GET", f"/resumes/{rid}/text", env.student).json()["text"]
    names = {s["skill_name"] for s in a["extracted"]["skills"]}
    assert names == {"Python", "SQL", "C++"}  # Rust/C/Kotlin never invented
    for s in a["extracted"]["skills"]:
        for sp in s["spans"]:
            assert text[sp["start"]: sp["end"]] == sp["text"]
    assert a["extracted"]["sections_found"] == ["Education", "Skills", "Projects"]
    assert a["extracted"]["projects"][0]["text"] == "Built a Python chatbot"
    assert a["notes"] == []
    latest = env.req("GET", f"/resumes/{rid}/analysis", env.student).json()
    assert latest["id"] == a["id"]
    r2 = env.req("POST", f"/resumes/{rid}/analyze", env.student, json={"jd_text": "Python"})
    hist = env.req("GET", f"/resumes/{rid}/analyses", env.student).json()
    assert [h["id"] for h in hist] == [r2.json()["id"], a["id"]]
    assert hist[0]["has_jd"] is True and hist[1]["has_jd"] is False
    assert hist[0]["role_name"] is None and hist[0]["role_match_percent"] is None


def test_analyze_role_and_jd_match(env: Env) -> None:
    rid = env.good()["id"]
    role = env.role()
    r = env.req(
        "POST", f"/resumes/{rid}/analyze", env.student,
        json={"role_id": role.id, "jd_text": "We want Python, Rust and Kotlin."},
    )
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["role_id"] == role.id and a["role_name"] == "Backend Dev"
    rm = a["role_match"]
    assert rm["match_percent"] == 66.67  # (3 + 1) / (3 + 1 + 2)
    assert [x["skill_name"] for x in rm["found"]] == ["Python", "SQL"]
    assert [x["skill_name"] for x in rm["missing"]] == ["Rust"]
    assert rm["found"][0] == {
        "skill_id": env.skills["Python"].id, "skill_name": "Python",
        "required_level": 60.0, "weight": 3.0,
    }
    jd = a["jd_match"]
    assert jd["match_percent"] == 50.0  # Python yes, Rust no; Kotlin is another college's
    assert {s["skill_name"]: s["in_resume"] for s in jd["skills_in_jd"]} == {
        "Python": True, "Rust": False,
    }
    hist = env.req("GET", f"/resumes/{rid}/analyses", env.student).json()
    assert hist[0]["role_match_percent"] == 66.67 and hist[0]["role_name"] == "Backend Dev"


def test_role_without_skills_and_jd_without_skills(env: Env) -> None:
    rid = env.good()["id"]
    role = env.role("Empty", with_skills=False)
    a = env.req(
        "POST", f"/resumes/{rid}/analyze", env.student,
        json={"role_id": role.id, "jd_text": "  nothing relevant  "},
    ).json()
    assert a["role_match"] == {"match_percent": None, "found": [], "missing": []}
    assert a["jd_match"] == {"match_percent": None, "skills_in_jd": []}
    assert len(a["notes"]) == 2
    blank = env.req("POST", f"/resumes/{rid}/analyze", env.student, json={"jd_text": "   "})
    assert blank.json()["jd_match"] is None


def test_role_visibility_404(env: Env) -> None:
    rid = env.good()["id"]
    dept = Department(college_id=env.a.id, name="Other", code="OT")
    env.db.add(dept)
    env.db.commit()
    hidden = [
        env.role("Inactive", active=False).id,
        env.role("OtherDept", dept=dept).id,
        env.role("ForeignCollege", college=env.b).id,
        999999,
    ]
    for role_id in hidden:
        r = env.req("POST", f"/resumes/{rid}/analyze", env.student, json={"role_id": role_id})
        assert r.status_code == 404, role_id
    assert env.db.execute(select(func.count()).select_from(ResumeAnalysis)).scalar_one() == 0


def test_jd_text_too_long_422(env: Env) -> None:
    rid = env.good()["id"]
    r = env.req("POST", f"/resumes/{rid}/analyze", env.student, json={"jd_text": "x" * 20001})
    assert r.status_code == 422
    ok = env.req("POST", f"/resumes/{rid}/analyze", env.student, json={"jd_text": "x" * 20000})
    assert ok.status_code == 201


def test_jd_text_not_stored(env: Env) -> None:
    rid = env.good()["id"]
    env.req(
        "POST", f"/resumes/{rid}/analyze", env.student,
        json={"jd_text": "Secret phrase zebra Python"},
    )
    row = env.db.execute(select(ResumeAnalysis)).scalars().one()
    assert "zebra" not in str(row.jd_match) and "zebra" not in str(row.extracted)


def test_analysis_deterministic_across_runs(env: Env) -> None:
    rid = env.good()["id"]
    a = env.req("POST", f"/resumes/{rid}/analyze", env.student, json={}).json()
    b = env.req("POST", f"/resumes/{rid}/analyze", env.student, json={}).json()
    assert a["extracted"] == b["extracted"] and a["id"] != b["id"]


# ---- storage unit -------------------------------------------------------------------------
def test_local_storage_roundtrip_and_traversal_guard(tmp_path: Path) -> None:
    from app.services.file_storage import LocalFileStorage

    store = LocalFileStorage(tmp_path)
    key = store.save(7, b"abc")
    assert store.read(key) == b"abc"
    store.delete(key)
    store.delete(key)  # idempotent
    assert not os.path.exists(tmp_path / key)
    with pytest.raises(ValueError):
        store.read("../outside")


# ---- analyze against an open job (Phase 7) -------------------------------------------------


def _job(env: Env, status: JobStatus = JobStatus.OPEN, college: College | None = None,
         body: str = "Knowledge of Rust is a plus") -> JobDescription:
    c = college or env.a
    admin = env.others[UserRole.ADMIN]
    company = Company(college_id=c.id, name=f"Co{c.id}{status.value}")
    env.db.add(company)
    env.db.commit()
    job = JobDescription(
        college_id=c.id, company_id=company.id, title="Backend Engineer", body=body,
        status=status, created_by=admin.id,
    )
    env.db.add(job)
    env.db.commit()
    return job


def test_analyze_with_job_id(env: Env) -> None:
    rid = env.good()["id"]
    job = _job(env)
    for nm, lvl in [("SQL", 50), ("Rust", 60)]:
        env.db.add(JobSkill(job_id=job.id, college_id=env.a.id, skill_id=env.skills[nm].id,
                            required_level=lvl, weight=1))
    env.db.commit()
    r = env.req("POST", f"/resumes/{rid}/analyze", env.student, json={"job_id": job.id})
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["job_id"] == job.id and a["job_title"] == "Backend Engineer"
    # job skills (SQL found, Rust missing); Rust also in body but not duplicated
    assert [(s["skill_name"], s["in_resume"]) for s in a["jd_match"]["skills_in_jd"]] == [
        ("Rust", False), ("SQL", True),
    ]
    assert a["jd_match"]["match_percent"] == 50.0
    assert a["role_match"] is None
    latest = env.req("GET", f"/resumes/{rid}/analysis", env.student).json()
    assert latest["job_id"] == job.id and latest["job_title"] == "Backend Engineer"
    hist = env.req("GET", f"/resumes/{rid}/analyses", env.student).json()
    assert hist[0]["has_jd"] is True


def test_analyze_with_job_body_skills_added(env: Env) -> None:
    rid = env.good()["id"]
    job = _job(env, body="We use Python daily and Rust sometimes")
    env.db.add(JobSkill(job_id=job.id, college_id=env.a.id, skill_id=env.skills["SQL"].id,
                        required_level=50, weight=1))
    env.db.commit()
    a = env.req("POST", f"/resumes/{rid}/analyze", env.student, json={"job_id": job.id}).json()
    got = {s["skill_name"]: s["in_resume"] for s in a["jd_match"]["skills_in_jd"]}
    assert got == {"SQL": True, "Python": True, "Rust": False}
    assert a["jd_match"]["match_percent"] == 66.67


def test_analyze_without_job_has_null_job_fields(env: Env) -> None:
    rid = env.good()["id"]
    a = env.req("POST", f"/resumes/{rid}/analyze", env.student, json={"jd_text": "Python"}).json()
    assert a["job_id"] is None and a["job_title"] is None


def test_analyze_job_id_and_jd_text_mutually_exclusive(env: Env) -> None:
    rid = env.good()["id"]
    job = _job(env)
    r = env.req("POST", f"/resumes/{rid}/analyze", env.student,
                json={"job_id": job.id, "jd_text": "Python"})
    assert r.status_code == 422
    blank = env.req("POST", f"/resumes/{rid}/analyze", env.student,
                    json={"job_id": job.id, "jd_text": "   "})
    assert blank.status_code == 201


def test_analyze_job_visibility_404(env: Env) -> None:
    rid = env.good()["id"]
    for job in (_job(env, JobStatus.CLOSED), _job(env, JobStatus.DRAFT),
                _job(env, college=env.b)):
        r = env.req("POST", f"/resumes/{rid}/analyze", env.student, json={"job_id": job.id})
        assert r.status_code == 404, job.status
    assert env.req("POST", f"/resumes/{rid}/analyze", env.student,
                   json={"job_id": 99999}).status_code == 404
    assert env.db.execute(select(func.count()).select_from(ResumeAnalysis)).scalar_one() == 0
