"""Seed script tests: admin email validation matches the login validator."""
import pytest
from pytest import MonkeyPatch

from scripts import seed_college


def test_validate_email_accepts_valid() -> None:
    assert seed_college.validate_email("admin@example.com") == "admin@example.com"


@pytest.mark.parametrize("email", ["admin@demo.local", "not-an-email", "a@b"])
def test_validate_email_rejects_invalid(email: str) -> None:
    with pytest.raises(ValueError, match="Invalid --admin-email"):
        seed_college.validate_email(email)


def test_main_exits_2_on_invalid_email(
    monkeypatch: MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "longenough1")
    code = seed_college.main(
        ["--name", "X", "--code", "X", "--admin-email", "admin@demo.local",
         "--admin-full-name", "Admin"]
    )
    assert code == 2
    assert "Invalid --admin-email" in capsys.readouterr().err
