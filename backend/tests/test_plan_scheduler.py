"""Unit tests for the pure plan scheduler."""
from app.services.plan_scheduler import (
    NO_RESOURCE_SUFFIX,
    REASSESS_TASK,
    GapInput,
    ResourceInput,
    build_schedule,
)


def gap(sid: int, name: str, priority: str, g: float | None, status: str = "GAP") -> GapInput:
    """Build a gap input."""
    return GapInput(sid, name, status, priority, g, f"Improve {name}")


def test_priority_then_gap_then_name_ordering() -> None:
    gaps = [
        gap(1, "B", "LOW", 10),
        gap(2, "A", "HIGH", 31),
        gap(3, "C", "HIGH", 45),
        gap(4, "D", "MEDIUM", 20),
        gap(5, "A2", "HIGH", 31),
    ]
    s = build_schedule(gaps, {}, 5)
    order = [i.skill_id for i in s.items if i.kind == "PRACTICE"]
    assert order == [3, 2, 5, 4, 1]
    assert not s.unscheduled


def test_skills_per_week_and_unscheduled_overflow() -> None:
    gaps = [gap(i, f"S{i}", "HIGH", 50 - i) for i in range(1, 9)]
    s = build_schedule(gaps, {}, 2)
    weeks = {w: [i.skill_id for i in s.items if i.week == w and i.kind == "PRACTICE"]
             for w in (1, 2, 3)}
    assert weeks == {1: [1, 2], 2: [3, 4], 3: [5, 6]}
    assert [g.skill_id for g in s.unscheduled] == [7, 8]


def test_no_evidence_goes_to_week_one_and_does_not_count() -> None:
    gaps = [
        gap(1, "Zed", "UNASSESSED", None, "NO_EVIDENCE"),
        gap(2, "Alpha", "UNASSESSED", None, "NO_EVIDENCE"),
        gap(3, "G1", "HIGH", 40),
        gap(4, "G2", "HIGH", 39),
    ]
    s = build_schedule(gaps, {}, 2)
    week1 = [i for i in s.items if i.week == 1]
    assert [i.kind for i in week1[:2]] == ["ASSESS", "ASSESS"]
    assert week1[0].task == "Take an assessment that covers Alpha"
    assert week1[1].task == "Take an assessment that covers Zed"
    assert {i.skill_id for i in week1 if i.kind == "PRACTICE"} == {3, 4}
    assert [i.position for i in week1] == list(range(1, len(week1) + 1))


def test_resources_limited_to_two_ordered_by_id_and_no_resource_wording() -> None:
    gaps = [gap(1, "Python", "HIGH", 40), gap(2, "SQL", "LOW", 5)]
    res = {1: [ResourceInput(9, "Third"), ResourceInput(3, "First"), ResourceInput(5, "Second")]}
    s = build_schedule(gaps, res, 2)
    learn = [i for i in s.items if i.kind == "LEARN"]
    assert [(i.resource_id, i.task) for i in learn] == [(3, "Study: First"), (5, "Study: Second")]
    practice = {i.skill_id: i for i in s.items if i.kind == "PRACTICE"}
    assert practice[1].task == "Practise Python: Improve Python"
    assert practice[2].task == "Practise SQL: Improve SQL" + NO_RESOURCE_SUFFIX
    assert practice[2].resource_id is None


def test_week_four_reassess_only_and_ready_skipped() -> None:
    gaps = [gap(1, "Done", "NONE", 0, "READY")]
    s = build_schedule(gaps, {}, 2)
    assert len(s.items) == 1
    only = s.items[0]
    assert (only.week, only.kind, only.task, only.skill_id) == (4, "REASSESS", REASSESS_TASK, None)
    assert not s.unscheduled


def test_deterministic() -> None:
    gaps = [gap(i, f"S{i}", "MEDIUM", 20) for i in range(6, 0, -1)]
    res = {1: [ResourceInput(1, "R")]}
    assert build_schedule(gaps, res, 2) == build_schedule(list(reversed(gaps)), res, 2)
