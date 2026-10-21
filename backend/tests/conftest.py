"""Test fixtures: PostgreSQL (the production database), TestClient, college and role users.

Each test runs inside a transaction that is rolled back afterwards, so tests are isolated and fast.
Start the throwaway database with ``docker compose -f docker-compose.test.yml up -d`` or point
TEST_DATABASE_URL at any PostgreSQL server (the database is created if it does not exist).
"""
import os

# Test-only credentials for the throwaway container in docker-compose.test.yml.
DEFAULT_TEST_DATABASE_URL = "postgresql://test:test@127.0.0.1:5434/gradnexa_test"
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["SMTP_HOST"] = ""
os.environ["BCRYPT_ROUNDS"] = "4"  # fast hashing in tests; production default is 12

from collections.abc import Callable, Generator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine, create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.auth.security import create_access_token, hash_password  # noqa: E402
from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, College, User, UserRole  # noqa: E402

PASSWORD = "Password123!"

_HELP = (
    "Cannot reach the test PostgreSQL at {url}.\n"
    "Start it with:  docker compose -f docker-compose.test.yml up -d\n"
    "or set TEST_DATABASE_URL to a PostgreSQL server you can create databases on."
)


def _ensure_database(url: str) -> None:
    """Create the test database if the server is up but the database does not exist yet."""
    target = make_url(url)
    try:
        create_engine(target, pool_pre_ping=True).connect().close()
        return
    except OperationalError:
        pass
    admin = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": target.database}
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    except OperationalError:
        pytest.exit(_HELP.format(url=target.render_as_string(hide_password=True)), returncode=2)
    finally:
        admin.dispose()


@pytest.fixture(scope="session")
def pg_engine() -> Generator[Engine, None, None]:
    """Engine for the test database; the schema is created once and dropped at the end."""
    _ensure_database(TEST_DATABASE_URL)
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db(pg_engine: Engine) -> Generator[Session, None, None]:
    """A session wrapped in an outer transaction that is rolled back after the test.

    ``session.commit()`` inside a test only releases a SAVEPOINT, so the data is visible to the
    app during the test and gone afterwards.
    """
    connection = pg_engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


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
