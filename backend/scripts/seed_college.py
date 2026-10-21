"""Seed a college and its ADMIN user. Idempotent.

Usage (from backend/):
    ADMIN_PASSWORD=... python -m scripts.seed_college --name "X College" --code XC \
        --admin-email a@x.edu --admin-full-name "Admin" [--departments "CS:CS,Mech:ME"]
The password is read only from the ADMIN_PASSWORD environment variable and never logged.
"""
import argparse
import logging
import os
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.database import SessionLocal
from app.logging_config import configure_logging
from app.models import College, Department, User, UserRole

logger = logging.getLogger("scripts.seed_college")
_EMAIL = TypeAdapter(EmailStr)


def validate_email(raw: str) -> str:
    """Validate with the same validator the auth schemas use (EmailStr); raise ValueError."""
    try:
        return str(_EMAIL.validate_python(raw))
    except ValidationError as exc:
        raise ValueError(f"Invalid --admin-email: {exc.errors()[0]['msg']}") from exc


def parse_departments(raw: str | None) -> list[tuple[str, str]]:
    """Parse "Name:CODE,Name:CODE" into (name, code) pairs."""
    pairs: list[tuple[str, str]] = []
    if not raw:
        return pairs
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        name, sep, code = chunk.rpartition(":")
        if not sep or not name.strip() or not code.strip():
            raise ValueError(f"Invalid department spec: {chunk!r}")
        pairs.append((name.strip(), code.strip().upper()))
    return pairs


def seed(
    db: Session,
    name: str,
    code: str,
    admin_email: str,
    admin_full_name: str,
    admin_password: str,
    departments: list[tuple[str, str]],
) -> None:
    """Create the college, ADMIN user and departments if missing."""
    college = db.execute(select(College).where(College.code == code)).scalar_one_or_none()
    if college is None:
        college = College(name=name, code=code)
        db.add(college)
        db.flush()
        logger.info("Created college code=%s", code)
    else:
        logger.info("College code=%s already exists", code)

    email = admin_email.lower()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        db.add(
            User(
                college_id=college.id,
                email=email,
                hashed_password=hash_password(admin_password),
                full_name=admin_full_name,
                role=UserRole.ADMIN,
                is_verified=True,
            )
        )
        logger.info("Created admin user")
    else:
        logger.info("Admin user already exists")

    for dept_name, dept_code in departments:
        exists = db.execute(
            select(Department.id).where(
                Department.college_id == college.id, Department.code == dept_code
            )
        ).first()
        if exists is None:
            db.add(Department(college_id=college.id, name=dept_name, code=dept_code))
            logger.info("Created department code=%s", dept_code)
    db.commit()


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Seed a college and its admin user")
    parser.add_argument("--name", required=True)
    parser.add_argument("--code", required=True)
    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--admin-full-name", required=True)
    parser.add_argument("--departments", default=None, help='"Name:CODE,Name:CODE"')
    args = parser.parse_args(argv)
    configure_logging("INFO")
    password = os.environ.get("ADMIN_PASSWORD", "")
    if len(password) < 8:
        logger.error("ADMIN_PASSWORD env var must be set (min 8 characters)")
        return 1
    try:
        args.admin_email = validate_email(args.admin_email)
        departments = parse_departments(args.departments)
    except ValueError as exc:
        logger.error("%s", exc)
        return 2
    with SessionLocal() as db:
        seed(
            db, args.name, args.code, args.admin_email, args.admin_full_name, password,
            departments,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
