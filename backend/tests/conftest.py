"""Test fixtures: in-memory SQLite DB, TestClient, college and role users."""
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["SMTP_HOST"] = ""
os.environ["BCRYPT_ROUNDS"] = "4"  # fast hashing in tests; production default is 12

from collections.abc import Callable, Generator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine, create_engine, text  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.auth.security import create_access_token, hash_password  # noqa: E402
from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, College, User, UserRole  # noqa: E402

PASSWORD = "Password123!"


TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture(scope="session")
def pg_engine() -> Generator[Engine | None, None, None]:
    """Optional real-database engine: set TEST_DATABASE_URL (e.g. Postgres) to use it.

    The schema is created once per session; tables are truncated between tests.
    Without TEST_DATABASE_URL the suite uses per-test in-memory SQLite.
    """
    if not TEST_DATABASE_URL:
        yield None
        return
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db(pg_engine: Engine | None) -> Generator[Session, None, None]:
    """Fresh database per test (in-memory SQLite, or TEST_DATABASE_URL when set)."""
    if pg_engine is not None:
        session = sessionmaker(bind=pg_engine, autoflush=False)()
        yield session
        session.rollback()
        session.close()
        tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
        with pg_engine.begin() as conn:
            conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        return
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    """TestClient using the test database."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def college(db: Session) -> College:
    """College A."""
    obj = College(name="College A", code="COLA")
    db.add(obj)
    db.commit()
    return obj


@pytest.fixture
def other_college(db: Session) -> College:
    """College B."""
    obj = College(name="College B", code="COLB")
    db.add(obj)
    db.commit()
    return obj


@pytest.fixture
def make_user(db: Session) -> Callable[..., User]:
    """Factory creating a user directly in the database."""

    def _make(
        college: College,
        role: UserRole = UserRole.STUDENT,
        email: str | None = None,
        password: str = PASSWORD,
    ) -> User:
        user = User(
            college_id=college.id,
            email=email or f"{role.value.lower()}-{college.code.lower()}@example.com",
            hashed_password=hash_password(password),
            full_name=f"{role.value} user",
            role=role,
            is_verified=True,
        )
        db.add(user)
        db.commit()
        return user

    return _make


@pytest.fixture
def users(college: College, make_user: Callable[..., User]) -> dict[UserRole, User]:
    """One user of each role in college A."""
    return {role: make_user(college, role) for role in UserRole}


@pytest.fixture
def auth_headers() -> Callable[[User], dict[str, str]]:
    """Build Authorization headers for a user."""

    def _headers(user: User) -> dict[str, str]:
        token = create_access_token(user.id, user.role.value, user.college_id)
        return {"Authorization": f"Bearer {token}"}

    return _headers
