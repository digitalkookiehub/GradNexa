"""Unit tests for the pure scoring function."""
from decimal import Decimal

from app.services.scoring import QuestionSpec, question_score, score_attempt

D = Decimal


def _q(qid: int, skill: int, correct: set[str], marks: str = "1") -> QuestionSpec:
    return QuestionSpec(id=qid, skill_id=skill, marks=D(marks), correct_option_ids=frozenset(correct))


def test_exact_match_single_and_multi() -> None:
    """Exact set equality earns the marks."""
    q = _q(1, 1, {"a", "b"}, "2")
    assert question_score(q, ["b", "a"], D("0")) == D("2")


def test_partial_multi_select_is_wrong() -> None:
    """A subset or superset of the correct set earns nothing and is penalised."""
    q = _q(1, 1, {"a", "b"}, "2")
    assert question_score(q, ["a"], D("0.5")) == D("-1.0")
    assert question_score(q, ["a", "b", "c"], D("0")) == D("0")


def test_unanswered_scores_zero_even_with_negative_marking() -> None:
    """Empty and missing answers are not penalised."""
    q = _q(1, 1, {"a"})
    assert question_score(q, [], D("1")) == D("0")
    assert question_score(q, None, D("1")) == D("0")


def test_negative_marking_and_floors() -> None:
    """Skill and total scores are floored at zero."""
    qs = [_q(1, 1, {"a"}), _q(2, 1, {"a"}), _q(3, 2, {"a"})]
    out = score_attempt(qs, {"1": ["x"], "2": ["x"], "3": ["a"]}, D("1"))
    assert out.per_skill[1].score == D("0")
    assert out.per_skill[1].percentage == D("0.00")
    assert out.per_skill[2].percentage == D("100.00")
    # raw total = -1 -1 +1 = -1 -> floored to 0
    assert out.total_score == D("0")
    assert out.max_score == D("3")
    assert out.percentage == D("0.00")


def test_rounding_half_up_two_dp() -> None:
    """Percentages round half-up to 2 dp."""
    qs = [_q(1, 1, {"a"}), _q(2, 1, {"a"}), _q(3, 1, {"a"})]
    out = score_attempt(qs, {"1": ["a"]}, D("0"))
    assert out.percentage == D("33.33")
    qs2 = [_q(i, 1, {"a"}) for i in range(1, 9)]
    out2 = score_attempt(qs2, {"1": ["a"]}, D("0"))
    assert out2.percentage == D("12.50")


def test_empty_assessment_and_counts() -> None:
    """No questions yields zeros; per-skill question counts are reported."""
    empty = score_attempt([], {}, D("0"))
    assert empty.percentage == D("0.00") and empty.per_skill == {}
    out = score_attempt([_q(1, 1, {"a"}), _q(2, 1, {"a"})], {}, D("0"))
    assert out.per_skill[1].question_count == 2


def test_deterministic() -> None:
    """Same inputs give identical outputs."""
    qs = [_q(1, 1, {"a"}), _q(2, 2, {"b"}, "3")]
    ans = {"1": ["a"], "2": ["c"]}
    assert score_attempt(qs, ans, D("0.25")) == score_attempt(qs, ans, D("0.25"))
