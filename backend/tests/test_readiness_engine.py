"""Unit tests for the pure readiness engine (no database)."""
import pytest

from app.services import readiness_engine as eng
from app.services.readiness_engine import (
    LevelThreshold,
    RoleRequirement,
    RuleConfig,
    SkillEvidence,
)


def rule(weights: dict[int, float] | None = None, high: float = 30, medium: float = 15) -> RuleConfig:
    return RuleConfig(
        rule_id=7,
        version=3,
        weights=weights if weights is not None else {1: 60, 2: 40},
        level_thresholds=[
            LevelThreshold("Beginner", 0),
            LevelThreshold("Strong", 80),
            LevelThreshold("Developing", 50),
        ],
        high_min_gap=high,
        medium_min_gap=medium,
    )


def ev(skill_id: int, cat: int, score: float, count: int = 1) -> SkillEvidence:
    return SkillEvidence(skill_id, f"S{skill_id}", cat, f"C{cat}", score, count, None)


def req(skill_id: int, cat: int, required: float, weight: float = 1) -> RoleRequirement:
    return RoleRequirement(skill_id, f"S{skill_id}", cat, f"C{cat}", required, weight)


NAMES = {1: "C1", 2: "C2"}


def test_general_weighted_mean_and_full_coverage() -> None:
    out = eng.compute_general(rule(), [ev(1, 1, 80), ev(2, 1, 60), ev(3, 2, 50)], NAMES)
    # cat1 mean 70 (w60), cat2 mean 50 (w40) -> (4200 + 2000) / 100 = 62
    assert out.overall == 62.0
    assert out.level == "Developing"
    assert out.coverage == 100.0
    assert [c.score for c in out.category_scores] == [70.0, 50.0]
    assert out.category_scores[0].evidence_count == 2
    assert len(out.evidence) == 3
    assert out.gaps == []


def test_general_renormalises_and_reports_coverage() -> None:
    out = eng.compute_general(rule(), [ev(1, 1, 90)], NAMES)
    assert out.overall == 90.0  # only category 1 counts, weights renormalised
    assert out.coverage == 60.0
    assert out.level == "Strong"
    missing = [c for c in out.category_scores if c.category_id == 2][0]
    assert missing.score is None and missing.evidence_count == 0


def test_general_ignores_skills_outside_weighted_categories() -> None:
    out = eng.compute_general(rule({1: 1}), [ev(1, 1, 40), ev(9, 5, 100)], NAMES)
    assert out.overall == 40.0
    assert [e.skill_id for e in out.evidence] == [1]


def test_general_zero_coverage_is_null() -> None:
    out = eng.compute_general(rule(), [], NAMES)
    assert out.overall is None and out.level is None and out.coverage == 0.0
    assert len(out.category_scores) == 2


def test_level_thresholds_boundaries() -> None:
    th = rule().level_thresholds
    assert eng.resolve_level(None, th) is None
    assert eng.resolve_level(0, th) == "Beginner"
    assert eng.resolve_level(49.99, th) == "Beginner"
    assert eng.resolve_level(50, th) == "Developing"
    assert eng.resolve_level(79.99, th) == "Developing"
    assert eng.resolve_level(80, th) == "Strong"
    assert eng.resolve_level(100, th) == "Strong"
    assert eng.resolve_level(10, [LevelThreshold("High", 60)]) is None


def test_determinism_same_inputs_same_output() -> None:
    skills = [ev(3, 2, 50), ev(1, 1, 80), ev(2, 1, 60)]
    a = eng.compute_general(rule(), skills, NAMES)
    b = eng.compute_general(rule(), list(reversed(skills)), NAMES)
    assert a == b
    reqs = [req(1, 1, 70), req(2, 1, 60, 2), req(4, 2, 50)]
    assert eng.compute_role(rule(), reqs, skills) == eng.compute_role(
        rule(), list(reversed(reqs)), skills
    )


def test_rounding_half_up() -> None:
    assert eng.round2(2.675) == 2.68
    assert eng.round2(1.005) == 1.01
    assert eng.round2(0.004) == 0.0
    out = eng.compute_general(rule({1: 1}), [ev(1, 1, 33.333), ev(2, 1, 33.333), ev(3, 1, 33.34)], NAMES)
    assert out.overall == 33.34


def test_role_score_weighted_by_role_skill_weight() -> None:
    reqs = [req(1, 1, 70, 3), req(2, 1, 70, 1), req(3, 2, 70, 4)]
    out = eng.compute_role(rule(), reqs, [ev(1, 1, 80), ev(2, 1, 40)])
    # (3*80 + 1*40) / 4 = 70 ; coverage 4/8 = 50
    assert out.overall == 70.0
    assert out.coverage == 50.0
    assert out.level == "Developing"
    cats = {c.category_id: c for c in out.category_scores}
    assert cats[1].score == 60.0 and cats[1].weight == 4.0 and cats[1].evidence_count == 2
    assert cats[2].score is None and cats[2].weight == 4.0


def test_role_zero_coverage_null_but_gaps_listed() -> None:
    out = eng.compute_role(rule(), [req(1, 1, 70)], [])
    assert out.overall is None and out.level is None and out.coverage == 0.0
    assert out.gaps[0].status == "NO_EVIDENCE"


def test_role_with_no_skills() -> None:
    out = eng.compute_role(rule(), [], [ev(1, 1, 50)])
    assert out.overall is None and out.coverage == 0.0 and out.gaps == []


def test_gap_no_evidence() -> None:
    g = eng.compute_role(rule(), [req(1, 1, 70)], []).gaps[0]
    assert (g.current, g.gap, g.status, g.priority) == (None, None, "NO_EVIDENCE", "UNASSESSED")
    assert g.recommended_action == "Complete an assessment that covers S1"


@pytest.mark.parametrize(
    ("current", "gap", "status", "priority"),
    [
        (70, 0.0, "READY", "NONE"),
        (90, 0.0, "READY", "NONE"),
        (69.99, 0.01, "GAP", "LOW"),
        (56, 14.0, "GAP", "LOW"),
        (55, 15.0, "GAP", "MEDIUM"),
        (41, 29.0, "GAP", "MEDIUM"),
        (40, 30.0, "GAP", "HIGH"),
        (0, 70.0, "GAP", "HIGH"),
    ],
)
def test_gap_status_priority_boundaries(
    current: float, gap: float, status: str, priority: str
) -> None:
    g = eng.compute_role(rule(), [req(1, 1, 70)], [ev(1, 1, current)]).gaps[0]
    assert (g.gap, g.status, g.priority) == (gap, status, priority)


def test_gap_action_texts() -> None:
    out = eng.compute_role(rule(), [req(1, 1, 70), req(2, 1, 50)], [ev(1, 1, 40), ev(2, 1, 60)])
    assert out.gaps[0].recommended_action == (
        "Improve S1: close a gap of 30 points (current 40, required 70)"
    )
    assert out.gaps[1].recommended_action == "No action needed"


def test_gap_rounding() -> None:
    g = eng.compute_role(rule(), [req(1, 1, 70.005)], [ev(1, 1, 50.1)]).gaps[0]
    assert g.gap == 19.91
