"""Unit tests for the pure eligibility engine."""
from decimal import Decimal

from app.services.eligibility_engine import (
    AVERAGE_ALL_SEMESTERS,
    ELIGIBLE,
    INCOMPLETE_DATA,
    LATEST_SEMESTER,
    MET,
    NO_RULE,
    NOT_ELIGIBLE,
    NOT_MET,
    UNKNOWN,
    RecordFact,
    RuleInput,
    StudentFacts,
    evaluate,
)


def rec(sem: int, cgpa: str, arrears: int = 0, att: str | None = "80") -> RecordFact:
    return RecordFact(sem, Decimal(cgpa), arrears, Decimal(att) if att is not None else None)


def facts(records: list[RecordFact] | None = None, dept: int | None = 1,
          year: int | None = 2026) -> StudentFacts:
    return StudentFacts(dept, year, records or [], "CSE" if dept else None)


def only(rule: RuleInput, student: StudentFacts) -> tuple[str, str, str | None]:
    out = evaluate(rule, student)
    assert len(out.criteria) == 1
    c = out.criteria[0]
    return c.result, out.status, c.actual


def test_no_rule_and_empty_rule_are_no_rule() -> None:
    assert evaluate(None, facts()).status == NO_RULE
    out = evaluate(RuleInput(custom_notes=["Bring ID"]), facts())
    assert out.status == NO_RULE and out.criteria == [] and out.custom_notes == ["Bring ID"]


def test_cgpa_latest_semester_uses_highest_semester_not_order() -> None:
    rule = RuleInput(cgpa_min=Decimal("7.5"), cgpa_basis=LATEST_SEMESTER)
    recs = [rec(3, "6.00"), rec(1, "9.00"), rec(2, "9.00")]
    assert only(rule, facts(recs)) == (NOT_MET, NOT_ELIGIBLE, "6.00")


def test_cgpa_average_is_plain_mean_not_weighted() -> None:
    rule = RuleInput(cgpa_min=Decimal("7.50"), cgpa_basis=AVERAGE_ALL_SEMESTERS)
    recs = [rec(1, "9.00"), rec(2, "6.00")]
    assert only(rule, facts(recs)) == (MET, ELIGIBLE, "7.50")  # equal is MET


def test_cgpa_boundaries_and_rounding() -> None:
    rule = RuleInput(cgpa_min=Decimal("7.00"), cgpa_basis=LATEST_SEMESTER)
    assert only(rule, facts([rec(1, "7.00")]))[0] == MET
    assert only(rule, facts([rec(1, "6.99")]))[0] == NOT_MET
    avg = RuleInput(cgpa_min=Decimal("7.00"), cgpa_basis=AVERAGE_ALL_SEMESTERS)
    # mean 6.995 is below 7.00 even though it displays as 7.00 (half-up of 6.995)
    result = only(avg, facts([rec(1, "6.99"), rec(2, "7.00")]))
    assert result == (NOT_MET, NOT_ELIGIBLE, "7.00")


def test_cgpa_no_records_unknown_and_default_basis() -> None:
    rule = RuleInput(cgpa_min=Decimal("7"))
    assert only(rule, facts([])) == (UNKNOWN, INCOMPLETE_DATA, None)
    assert only(rule, facts([rec(1, "8"), rec(2, "7")]))[0] == MET  # defaults to latest


def test_arrears() -> None:
    rule = RuleInput(max_arrears=1)
    assert only(rule, facts([rec(1, "8", 5), rec(2, "8", 1)]))[0] == MET
    assert only(rule, facts([rec(1, "8", 0), rec(2, "8", 2)])) == (NOT_MET, NOT_ELIGIBLE, "2")
    assert only(rule, facts([]))[0] == UNKNOWN
    assert only(RuleInput(max_arrears=0), facts([rec(1, "8", 0)]))[0] == MET


def test_attendance() -> None:
    rule = RuleInput(attendance_min=Decimal("75"))
    assert only(rule, facts([rec(1, "8", att="75")]))[0] == MET
    assert only(rule, facts([rec(1, "8", att="74.99")]))[0] == NOT_MET
    # latest semester has null attendance: older semesters are not consulted
    assert only(rule, facts([rec(1, "8", att="90"), rec(2, "8", att=None)]))[0] == UNKNOWN
    assert only(rule, facts([]))[0] == UNKNOWN


def test_department() -> None:
    rule = RuleInput(department_ids=[1, 2], department_names={1: "CSE", 2: "ECE"})
    assert only(rule, facts(dept=1)) == (MET, ELIGIBLE, "CSE")
    assert only(rule, facts(dept=3))[0] == NOT_MET
    assert only(rule, facts(dept=None))[0] == UNKNOWN
    assert "CSE" in evaluate(rule, facts()).criteria[0].required


def test_graduation_year() -> None:
    rule = RuleInput(graduation_years=[2026, 2027])
    assert only(rule, facts(year=2027))[0] == MET
    assert only(rule, facts(year=2025))[0] == NOT_MET
    assert only(rule, facts(year=None))[0] == UNKNOWN


def test_status_precedence() -> None:
    rule = RuleInput(cgpa_min=Decimal("9"), max_arrears=0, graduation_years=[2026])
    # NOT_MET beats UNKNOWN
    out = evaluate(rule, facts([rec(1, "5")], year=None))
    assert {c.key: c.result for c in out.criteria} == {
        "cgpa": NOT_MET, "arrears": MET, "graduation_year": UNKNOWN,
    }
    assert out.status == NOT_ELIGIBLE
    # UNKNOWN beats MET
    assert evaluate(rule, facts([rec(1, "9.5")], year=None)).status == INCOMPLETE_DATA
    assert evaluate(rule, facts([rec(1, "9.5")], year=2026)).status == ELIGIBLE


def test_custom_notes_never_evaluated() -> None:
    notes = ["No history of backlogs", "CGPA above 10"]
    out = evaluate(RuleInput(max_arrears=0, custom_notes=notes), facts([rec(1, "1")]))
    assert out.status == ELIGIBLE and out.custom_notes == notes
    assert [c.key for c in out.criteria] == ["arrears"]


def test_deterministic() -> None:
    rule = RuleInput(
        cgpa_min=Decimal("7"), cgpa_basis=AVERAGE_ALL_SEMESTERS, max_arrears=1,
        attendance_min=Decimal("70"), department_ids=[1], graduation_years=[2026],
    )
    student = facts([rec(1, "7.1"), rec(2, "8.2", 1, "71")])
    first = evaluate(rule, student)
    assert all(evaluate(rule, student) == first for _ in range(5))
    assert [c.key for c in first.criteria] == [
        "cgpa", "arrears", "attendance", "department", "graduation_year",
    ]
