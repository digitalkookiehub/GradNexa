# ruff: noqa: F811
"""MCP registry, schemas, authorization matrix, validation and audit tests."""
from typing import Any

from sqlalchemy import select

from app.mcp.registry import REGISTRY
from app.models import AuditLog, Department, MCPTool
from app.models.job_description import JobStatus
from tests.test_mcp_env import McpEnv, menv  # noqa: F401

STUDENT_TOOLS = [
    "get_student_profile",
    "get_student_academic_record",
    "get_student_assessment_results",
    "get_student_skill_scores",
    "get_student_progress",
]


def test_registry_shape() -> None:
    assert len(REGISTRY) == 9
    for d in REGISTRY.values():
        assert d.description and d.allowed_roles
        assert d.input_model.model_json_schema()["type"] == "object"
        assert d.output_model.model_json_schema()["type"] == "object"


def test_list_tools_per_role(menv: McpEnv) -> None:
    r = menv.req("GET", "/mcp/tools", menv.student)
    assert r.status_code == 200
    names = {t["name"] for t in r.json()}
    assert names == set(REGISTRY)
    assert all(t["enabled"] is True and t["input_schema"] and t["output_schema"] for t in r.json())
    hod = {t["name"] for t in menv.req("GET", "/mcp/tools", menv.hod).json()}
    assert hod == {
        "get_department_details", "get_eligibility_rules",
        "get_company_requirements", "get_job_description",
    }
    assert menv.client.get("/api/v1/mcp/tools").status_code == 401


def test_student_self_tools_and_output(menv: McpEnv) -> None:
    for name in STUDENT_TOOLS:
        r = menv.call(name, menv.student)
        assert r.status_code == 200, (name, r.text)
        body = r.json()
        assert body["tool"] == name
        assert body["result"]["student_id"] == menv.s1.id
        assert REGISTRY[name].output_model.model_validate(body["result"])
        assert menv.call(name, menv.student, {"student_id": menv.s1.id}).status_code == 200
    prof = menv.call("get_student_profile", menv.student).json()["result"]
    assert prof["roll_number"] == "R-ONE" and prof["department_name"] == "Dept CS"
    assert "email" not in prof and "phone" not in prof
    acad = menv.call("get_student_academic_record", menv.student).json()["result"]
    assert acad["latest_cgpa"] == 8.1 and acad["latest_attendance_pct"] == 88.0


def test_student_cannot_read_others(menv: McpEnv) -> None:
    for name in STUDENT_TOOLS:
        assert menv.call(name, menv.student, {"student_id": menv.s2.id}).status_code == 404
        assert menv.call(name, menv.student, {"student_id": menv.sb.id}).status_code == 404


def test_faculty_matrix(menv: McpEnv) -> None:
    for name in STUDENT_TOOLS:
        assert menv.call(name, menv.faculty, {"student_id": menv.s1.id}).status_code == 404
        assert menv.call(name, menv.faculty).status_code == 422
    menv.assign(menv.faculty, menv.s1)
    for name in STUDENT_TOOLS:
        assert menv.call(name, menv.faculty, {"student_id": menv.s1.id}).status_code == 200
        assert menv.call(name, menv.faculty, {"student_id": menv.s2.id}).status_code == 404


def test_tpo_admin_same_college_only(menv: McpEnv) -> None:
    for user in (menv.tpo, menv.admin):
        for name in STUDENT_TOOLS:
            assert menv.call(name, user, {"student_id": menv.s2.id}).status_code == 200
            assert menv.call(name, user, {"student_id": menv.sb.id}).status_code == 404
    for name in STUDENT_TOOLS:
        assert menv.call(name, menv.tpo_b, {"student_id": menv.s1.id}).status_code == 404


def test_hod_and_super_admin_denied_student_tools(menv: McpEnv) -> None:
    for user in (menv.hod, menv.super_admin):
        for name in STUDENT_TOOLS:
            r = menv.call(name, user, {"student_id": menv.s1.id})
            assert r.status_code == 403
            assert r.json() == {"detail": "Insufficient permissions"}


def test_unknown_tool_and_validation(menv: McpEnv) -> None:
    assert menv.call("drop_tables", menv.student).status_code == 404
    bad: list[tuple[str, dict[str, Any]]] = [
        ("get_student_profile", {"student_id": "abc"}),
        ("get_student_profile", {"student_id": 0}),
        ("get_student_profile", {"sql": "select 1"}),
        ("get_student_assessment_results", {"limit": 0}),
        ("get_student_assessment_results", {"limit": 51}),
        ("get_job_description", {}),
        ("get_job_description", {"job_id": -1}),
        ("get_company_requirements", {"company_id": "x"}),
    ]
    for name, args in bad:
        r = menv.call(name, menv.student, args)
        assert r.status_code == 422, (name, args, r.text)
        assert "detail" in r.json()
    r = menv.req(
        "POST", "/mcp/tools/get_student_profile/call", menv.student, json={"arguments": [1]}
    )
    assert r.status_code == 422


def test_disabled_tool_403(menv: McpEnv) -> None:
    r = menv.req(
        "PUT", "/admin/mcp-tools/get_student_profile", menv.admin, json={"enabled": False}
    )
    assert r.status_code == 200 and r.json()["enabled"] is False
    d = menv.call("get_student_profile", menv.student)
    assert d.status_code == 403 and d.json() == {"detail": "Tool disabled"}
    listed = {t["name"]: t["enabled"] for t in menv.req("GET", "/mcp/tools", menv.student).json()}
    assert listed["get_student_profile"] is False
    assert menv.call("get_student_profile", menv.student_b).status_code == 200
    menv.req("PUT", "/admin/mcp-tools/get_student_profile", menv.admin, json={"enabled": True})
    assert menv.call("get_student_profile", menv.student).status_code == 200
    assert len(menv.db.execute(select(MCPTool)).scalars().all()) == 1


def test_admin_mcp_endpoints(menv: McpEnv) -> None:
    r = menv.req("GET", "/admin/mcp-tools", menv.admin)
    assert r.status_code == 200
    assert {i["name"] for i in r.json()} == set(REGISTRY)
    item = next(i for i in r.json() if i["name"] == "get_student_profile")
    assert item["enabled"] is True and "STUDENT" in item["allowed_roles"]
    assert "HOD" not in item["allowed_roles"]
    for user in (menv.student, menv.faculty, menv.tpo, menv.hod):
        assert menv.req("GET", "/admin/mcp-tools", user).status_code == 403
        assert menv.req(
            "PUT", "/admin/mcp-tools/get_student_profile", user, json={"enabled": False}
        ).status_code == 403
    assert menv.req(
        "PUT", "/admin/mcp-tools/nope", menv.admin, json={"enabled": False}
    ).status_code == 404
    assert menv.req(
        "PUT", "/admin/mcp-tools/get_student_profile", menv.admin, json={}
    ).status_code == 422
    menv.req("PUT", "/admin/mcp-tools/get_student_profile", menv.admin, json={"enabled": False})
    assert "MCP_TOOL_TOGGLE" in menv.actions()


def test_audit_keys_only(menv: McpEnv) -> None:
    menv.call("get_student_profile", menv.student, {"student_id": menv.s1.id})
    menv.call("get_student_profile", menv.student, {"student_id": menv.s2.id})
    rows = list(
        menv.db.execute(
            select(AuditLog).where(AuditLog.action == "MCP_TOOL_CALL").order_by(AuditLog.id)
        ).scalars()
    )
    assert len(rows) == 2
    ok, denied = rows
    assert ok.metadata_json == {
        "tool": "get_student_profile", "argument_keys": ["student_id"],
        "outcome": "ok", "student_id": menv.s1.id,
    }
    assert denied.metadata_json is not None
    assert denied.metadata_json["outcome"] == "error_404"
    assert "student_id" not in denied.metadata_json
    assert ok.user_id == menv.student.id and ok.college_id == menv.a.id


def test_department_tool(menv: McpEnv) -> None:
    menv.role_named()
    r = menv.call("get_department_details", menv.student)
    assert r.status_code == 200 and r.json()["result"]["department_id"] == menv.dept_a.id
    r = menv.call("get_department_details", menv.hod, {"department_id": menv.dept_a.id})
    assert r.status_code == 200 and r.json()["result"]["code"] == "CS"
    assert menv.call("get_department_details", menv.hod).status_code == 422
    other = menv.db.execute(
        select(Department).where(Department.college_id == menv.b.id)
    ).scalars().first()
    assert other is not None
    assert menv.call(
        "get_department_details", menv.hod, {"department_id": other.id}
    ).status_code == 404
    assert menv.call("get_department_details", menv.student_b).status_code == 200


def test_department_tool_student_without_department(menv: McpEnv) -> None:
    menv.s2.department_id = None
    menv.db.commit()
    assert menv.call("get_department_details", menv.student2).status_code == 404


def test_job_company_eligibility_tools(menv: McpEnv) -> None:
    job = menv.company_job(menv.a)
    draft = menv.company_job(menv.a, JobStatus.DRAFT, name="Hidden")
    other = menv.company_job(menv.b, name="BCorp")
    r = menv.call("get_job_description", menv.student, {"job_id": job.id})
    assert r.status_code == 200
    res = r.json()["result"]
    assert res["title"] == "Acme Job" and res["skills"][0]["skill_name"] == "Python"
    assert res["eligibility_criteria"]["cgpa_min"] == 7.5
    assert menv.call("get_job_description", menv.student, {"job_id": draft.id}).status_code == 404
    assert menv.call("get_job_description", menv.tpo, {"job_id": draft.id}).status_code == 200
    assert menv.call("get_job_description", menv.student, {"job_id": other.id}).status_code == 404
    assert menv.call("get_job_description", menv.hod, {"job_id": job.id}).status_code == 200
    e = menv.call("get_eligibility_rules", menv.student, {"job_id": job.id}).json()["result"]
    assert e["has_rule"] and e["evaluation"]["status"] == "ELIGIBLE"
    e2 = menv.call("get_eligibility_rules", menv.hod, {"job_id": job.id}).json()["result"]
    assert e2["evaluation"] is None and e2["criteria"]["max_arrears"] == 0
    assert menv.call(
        "get_eligibility_rules", menv.student, {"job_id": job.id, "student_id": menv.s2.id}
    ).status_code == 404
    e3 = menv.call(
        "get_eligibility_rules", menv.tpo, {"job_id": job.id, "student_id": menv.s2.id}
    ).json()["result"]
    assert e3["evaluation"]["status"] == "INCOMPLETE_DATA"
    c = menv.call(
        "get_company_requirements", menv.student, {"company_id": job.company_id}
    ).json()["result"]
    assert [j["job_id"] for j in c["open_jobs"]] == [job.id]
    assert c["open_jobs"][0]["skills"][0]["skill_name"] == "Python"
    assert menv.call(
        "get_company_requirements", menv.student, {"company_id": other.company_id}
    ).status_code == 404
    hidden = menv.call(
        "get_company_requirements", menv.tpo, {"company_id": draft.company_id}
    ).json()["result"]
    assert hidden["open_jobs"] == []


def test_progress_and_skill_tools_with_data(menv: McpEnv) -> None:
    menv.active_rule()
    role = menv.role_named()
    menv.give_score(menv.s1, menv.py, 40)
    assert menv.req(
        "POST", "/readiness/compute", menv.student, json={"role_id": role}
    ).status_code == 201
    p = menv.call("get_student_progress", menv.student, {"role_id": role}).json()["result"]
    rd = p["latest_readiness"]
    assert rd["role_id"] == role and rd["gaps"] and rd["gaps"][0]["priority"] == "HIGH"
    assert p["plan"] is None
    sk = menv.call("get_student_skill_scores", menv.student).json()["result"]["skills"]
    assert sk[0]["skill_name"] == "Python" and sk[0]["score"] == 40.0
    res = menv.call("get_student_assessment_results", menv.student, {"limit": 3})
    assert res.json()["result"]["results"] == []


def test_cross_college_student_id(menv: McpEnv) -> None:
    for name in STUDENT_TOOLS:
        assert menv.call(name, menv.admin_b, {"student_id": menv.s1.id}).status_code == 404
