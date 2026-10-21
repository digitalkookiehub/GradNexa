"""Pure, deterministic job-eligibility engine (no I/O, no LLM, no randomness).

Eligibility is SEPARATE from readiness: it only checks the criteria an admin configured on a
job's eligibility rule against recorded student facts. It never produces a score, probability
or selection prediction, and nothing here is ever combined with readiness.

Rules (every one is an assumption about unknown institutional policy):
1. A criterion is evaluated ONLY when the rule sets it (value is not None). Unset criteria are
   omitted from the result entirely.
2. cgpa: basis LATEST_SEMESTER = cgpa of the academic record with the highest semester;
   AVERAGE_ALL_SEMESTERS = plain arithmetic mean of all records' cgpa (NOT credit-weighted).
   actual >= cgpa_min -> MET (equal is MET); actual < cgpa_min -> NOT_MET; no records -> UNKNOWN.
   A missing basis defaults to LATEST_SEMESTER.
3. arrears: active_arrears of the latest-semester record <= max_arrears -> MET, else NOT_MET;
   no records -> UNKNOWN.
4. attendance: attendance_pct of the latest-semester record >= attendance_min -> MET (equal is
   MET), lower -> NOT_MET; null attendance or no records -> UNKNOWN (older semesters are not
   consulted).
5. department: student's department_id in department_ids -> MET, not in -> NOT_MET; student
   has no department -> UNKNOWN. An empty list means "no department qualifies".
6. graduation_year: student's graduation_year in graduation_years likewise; none -> UNKNOWN.
7. Overall status: NOT_ELIGIBLE if any criterion is NOT_MET; else INCOMPLETE_DATA if any is
   UNKNOWN; else ELIGIBLE. If no criterion is automatically evaluable (or there is no rule at
   all) the status is NO_RULE.
8. custom_notes are returned verbatim and are NEVER evaluated.
9. Comparisons use Decimal; displayed values are rounded half-up to 2 decimal places.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

MET = "MET"
NOT_MET = "NOT_MET"
UNKNOWN = "UNKNOWN"

ELIGIBLE = "ELIGIBLE"
NOT_ELIGIBLE = "NOT_ELIGIBLE"
INCOMPLETE_DATA = "INCOMPLETE_DATA"
NO_RULE = "NO_RULE"

LATEST_SEMESTER = "LATEST_SEMESTER"
AVERAGE_ALL_SEMESTERS = "AVERAGE_ALL_SEMESTERS"

_TWO = Decimal("0.01")


@dataclass(frozen=True)
class RuleInput:
    """Eligibility rule data (only the set criteria are evaluated)."""

    cgpa_min: Decimal | None = None
    cgpa_basis: str | None = None
    max_arrears: int | None = None
    attendance_min: Decimal | None = None
    department_ids: Sequence[int] | None = None
    graduation_years: Sequence[int] | None = None
    custom_notes: Sequence[str] = ()
    department_names: Mapping[int, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RecordFact:
    """One academic record."""

    semester: int
    cgpa: Decimal
    active_arrears: int
    attendance_pct: Decimal | None


@dataclass(frozen=True)
class StudentFacts:
    """Student facts the engine may use."""

    department_id: int | None
    graduation_year: int | None
    records: Sequence[RecordFact] = ()
    department_name: str | None = None


@dataclass(frozen=True)
class Criterion:
    """One evaluated criterion."""

    key: str
    label: str
    required: str
    actual: str | None
    result: str


@dataclass(frozen=True)
class EligibilityResult:
    """Engine output."""

    status: str
    criteria: list[Criterion]
    custom_notes: list[str]


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def fmt2(value: Decimal) -> str:
    """Display a Decimal rounded half-up to 2 decimal places."""
    return str(value.quantize(_TWO, rounding=ROUND_HALF_UP))


def _latest(records: Sequence[RecordFact]) -> RecordFact | None:
    return max(records, key=lambda r: r.semester) if records else None


def _cgpa(minimum_raw: Decimal, rule: RuleInput, student: StudentFacts) -> Criterion:
    basis = rule.cgpa_basis or LATEST_SEMESTER
    minimum = _d(minimum_raw)
    scope = "average of all semesters" if basis == AVERAGE_ALL_SEMESTERS else "latest semester"
    required = f">= {fmt2(minimum)} ({scope})"
    actual: Decimal | None = None
    if student.records:
        if basis == AVERAGE_ALL_SEMESTERS:
            total = sum((_d(r.cgpa) for r in student.records), Decimal(0))
            actual = total / len(student.records)
        else:
            latest = _latest(student.records)
            actual = _d(latest.cgpa) if latest is not None else None
    if actual is None:
        return Criterion("cgpa", "CGPA", required, None, UNKNOWN)
    result = MET if actual >= minimum else NOT_MET
    return Criterion("cgpa", "CGPA", required, fmt2(actual), result)


def _arrears(maximum: int, student: StudentFacts) -> Criterion:
    required = f"<= {maximum} (latest semester)"
    latest = _latest(student.records)
    if latest is None:
        return Criterion("arrears", "Active arrears", required, None, UNKNOWN)
    result = MET if latest.active_arrears <= maximum else NOT_MET
    return Criterion("arrears", "Active arrears", required, str(latest.active_arrears), result)


def _attendance(minimum_raw: Decimal, student: StudentFacts) -> Criterion:
    minimum = _d(minimum_raw)
    required = f">= {fmt2(minimum)}% (latest semester)"
    latest = _latest(student.records)
    if latest is None or latest.attendance_pct is None:
        return Criterion("attendance", "Attendance", required, None, UNKNOWN)
    actual = _d(latest.attendance_pct)
    result = MET if actual >= minimum else NOT_MET
    return Criterion("attendance", "Attendance", required, f"{fmt2(actual)}%", result)


def _department(ids: Sequence[int], rule: RuleInput, student: StudentFacts) -> Criterion:
    names = [rule.department_names.get(i, f"Department {i}") for i in ids]
    required = "One of: " + ", ".join(names) if names else "No department qualifies"
    if student.department_id is None:
        return Criterion("department", "Department", required, None, UNKNOWN)
    actual = student.department_name or f"Department {student.department_id}"
    result = MET if student.department_id in ids else NOT_MET
    return Criterion("department", "Department", required, actual, result)


def _grad_year(years_raw: Sequence[int], student: StudentFacts) -> Criterion:
    years = sorted(set(years_raw))
    required = "One of: " + ", ".join(str(y) for y in years) if years else "No year qualifies"
    if student.graduation_year is None:
        return Criterion("graduation_year", "Graduation year", required, None, UNKNOWN)
    result = MET if student.graduation_year in years else NOT_MET
    return Criterion(
        "graduation_year", "Graduation year", required, str(student.graduation_year), result
    )


def evaluate(rule: RuleInput | None, student: StudentFacts) -> EligibilityResult:
    """Evaluate the rule's set criteria against the student's facts."""
    if rule is None:
        return EligibilityResult(NO_RULE, [], [])
    criteria: list[Criterion] = []
    if rule.cgpa_min is not None:
        criteria.append(_cgpa(rule.cgpa_min, rule, student))
    if rule.max_arrears is not None:
        criteria.append(_arrears(rule.max_arrears, student))
    if rule.attendance_min is not None:
        criteria.append(_attendance(rule.attendance_min, student))
    if rule.department_ids is not None:
        criteria.append(_department(rule.department_ids, rule, student))
    if rule.graduation_years is not None:
        criteria.append(_grad_year(rule.graduation_years, student))
    notes = [str(n) for n in rule.custom_notes]
    results = {c.result for c in criteria}
    if not criteria:
        status = NO_RULE
    elif NOT_MET in results:
        status = NOT_ELIGIBLE
    elif UNKNOWN in results:
        status = INCOMPLETE_DATA
    else:
        status = ELIGIBLE
    return EligibilityResult(status, criteria, notes)
