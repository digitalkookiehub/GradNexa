"""Health endpoint tests."""
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app


def test_health(client: TestClient) -> None:
    """Liveness returns ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_ok(client: TestClient) -> None:
    """Readiness returns 200 when DB is reachable."""
    assert client.get("/health/ready").status_code == 200


def test_ready_db_down(client: TestClient, db: Session) -> None:
    """Readiness returns 503 when DB is down."""

    class BrokenSession:
        def execute(self, *args: object, **kwargs: object) -> None:
            raise OperationalError("SELECT 1", {}, Exception("down"))

        def close(self) -> None:
            return None

    app.dependency_overrides[get_db] = lambda: BrokenSession()
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert "detail" in response.json()
