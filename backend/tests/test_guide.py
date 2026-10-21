"""In-app flow guide: ADMIN only, authenticated, content is internally consistent."""
import re
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.models import User, UserRole
from app.services import guide_service


def test_admin_reads_guide(
    client: TestClient, users: dict[UserRole, User], auth_headers: Callable[[User], dict[str, str]]
) -> None:
    res = client.get("/api/v1/guide", headers=auth_headers(users[UserRole.ADMIN]))
    assert res.status_code == 200
    body = res.json()
    assert body["title"] == "GradNexa User Guide"
    assert [g["id"] for g in body["groups"]] == ["account", "admin", "config", "student", "staff", "reference"]
    assert len(body["overview"]) >= 5
    assert "Part 1" in body["markdown"]


@pytest.mark.parametrize(
    "role", [UserRole.STUDENT, UserRole.FACULTY, UserRole.TPO, UserRole.HOD, UserRole.SUPER_ADMIN]
)
def test_other_roles_forbidden(
    client: TestClient,
    users: dict[UserRole, User],
    auth_headers: Callable[[User], dict[str, str]],
    role: UserRole,
) -> None:
    assert client.get("/api/v1/guide", headers=auth_headers(users[role])).status_code == 403


def test_unauthenticated_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/guide").status_code == 401


def _procedures() -> list:  # type: ignore[type-arg]
    return [p for g in guide_service.load_document().groups for p in g.procedures]


def test_overview_and_next_links_point_to_real_procedures() -> None:
    ids = {p.id for p in _procedures()}
    doc = guide_service.load_document()
    assert all(item.goto in ids for item in doc.overview)
    assert all(p.next in ids for p in _procedures() if p.next)


def test_ids_unique_and_every_procedure_is_usable() -> None:
    procedures = _procedures()
    ids = [p.id for p in procedures]
    assert len(ids) == len(set(ids))
    for p in procedures:
        assert p.steps or p.terms or p.tables, p.id
        for table in p.tables:
            assert table.rows, (p.id, table.title)
            assert all(len(row) == len(table.columns) for row in table.rows), (p.id, table.title)
        for step in p.steps:
            assert step.do.strip(), p.id
        assert p.path is None or p.path.startswith("/"), p.id
        assert p.next != p.id


def test_step_paths_exist_in_the_frontend_router() -> None:
    """Every page path named in the guide must be a real route in the frontend App.tsx."""
    app_tsx = Path(__file__).resolve().parents[2] / "frontend" / "src" / "App.tsx"
    if not app_tsx.exists():
        pytest.skip("frontend sources not present (backend-only checkout)")
    routes = app_tsx.read_text(encoding="utf-8")
    for p in _procedures():
        if p.path:
            assert f'path="{p.path}"' in routes, f"{p.id}: {p.path} is not a route"


def test_guide_contains_no_secrets() -> None:
    """The guide may show placeholders like <strong password>, never a concrete credential."""
    text = guide_service.FLOW_PATH.read_text(encoding="utf-8") + guide_service.GUIDE_PATH.read_text(
        encoding="utf-8"
    )
    for needle in ("SECRET_KEY=", "POSTGRES_PASSWORD="):
        assert needle not in text
    concrete = re.findall(r"(?i)password\s*[:=]\s*['\"]?(?!<)[A-Za-z0-9#@!$%^&*]{6,}", text)
    assert concrete == [], concrete


def test_missing_file_gives_404(
    client: TestClient,
    users: dict[UserRole, User],
    auth_headers: Callable[[User], dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(guide_service, "FLOW_PATH", tmp_path / "nope.json")
    res = client.get("/api/v1/guide", headers=auth_headers(users[UserRole.ADMIN]))
    assert res.status_code == 404


def test_configuration_group_covers_every_admin_setting() -> None:
    """The configuration reference must keep a sample-bearing page per configurable area."""
    doc = guide_service.load_document()
    config = next(g for g in doc.groups if g.id == "config")
    ids = {p.id for p in config.procedures}
    assert {
        "c-overview", "c-departments", "c-skills", "c-roles", "c-rule", "c-assessments",
        "c-resources", "c-interview", "c-jobs", "c-knowledge", "c-access", "c-operator", "c-decisions",
    } <= ids
    for p in config.procedures:
        assert p.tables, p.id
