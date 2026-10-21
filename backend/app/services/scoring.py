"""Pure, deterministic assessment scoring. No I/O, no database, no LLM.

Rules (per question):
* correct iff the selected option set EXACTLY equals ``correct_option_ids``  -> ``+marks``
* unanswered / empty selection -> ``0``
* answered but wrong (including partially correct multi-select)
  -> ``-(negative_marking * marks)``

Aggregation:
* per-skill score = sum of that skill's question scores, floored at 0
* total_score     = sum of ALL question scores, floored at 0
* max_score       = sum of all question marks
* percentage      = score / max * 100, rounded half-up to 2 decimal places (0 when max is 0)

ASSUMPTIONS (not confirmed institutional policy; revisit with stakeholders):
1. Per-skill and total scores are floored at 0 (negative marking can never push a score below zero).
2. A skill's stored StudentSkill score is the percentage of the LATEST result that covered it
   (latest-result-wins); older results are not averaged in.
3. Partial credit for multi-select questions is NOT given: a partially correct set is wrong.
"""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_TWO_DP = Decimal("0.01")


@dataclass(frozen=True)
class QuestionSpec:
    """Scoring-relevant view of a question."""

    id: int
    skill_id: int
    marks: Decimal
    correct_option_ids: frozenset[str]


@dataclass(frozen=True)
class SkillScore:
    """Score of one skill within an attempt."""

    skill_id: int
    score: Decimal
    max: Decimal
    percentage: Decimal
    question_count: int


@dataclass(frozen=True)
class ScoreOutcome:
    """Full scoring outcome of an attempt."""

    total_score: Decimal
    max_score: Decimal
    percentage: Decimal
    per_skill: dict[int, SkillScore]


def _pct(score: Decimal, maximum: Decimal) -> Decimal:
    if maximum <= 0:
        return Decimal("0.00")
    return (score / maximum * 100).quantize(_TWO_DP, rounding=ROUND_HALF_UP)


def question_score(
    question: QuestionSpec, selected: Sequence[str] | None, negative_marking: Decimal
) -> Decimal:
    """Score a single question for the selected option ids."""
    chosen = frozenset(selected or ())
    if not chosen:
        return Decimal("0")
    if chosen == question.correct_option_ids:
        return question.marks
    return -(negative_marking * question.marks)


def score_attempt(
    questions: Sequence[QuestionSpec],
    answers: Mapping[str, Sequence[str]],
    negative_marking: Decimal,
) -> ScoreOutcome:
    """Score all questions; ``answers`` maps str(question_id) to selected option ids."""
    raw_total = Decimal("0")
    max_total = Decimal("0")
    skill_raw: dict[int, Decimal] = {}
    skill_max: dict[int, Decimal] = {}
    skill_count: dict[int, int] = {}
    for q in questions:
        s = question_score(q, answers.get(str(q.id)), negative_marking)
        raw_total += s
        max_total += q.marks
        skill_raw[q.skill_id] = skill_raw.get(q.skill_id, Decimal("0")) + s
        skill_max[q.skill_id] = skill_max.get(q.skill_id, Decimal("0")) + q.marks
        skill_count[q.skill_id] = skill_count.get(q.skill_id, 0) + 1
    total = max(raw_total, Decimal("0"))
    per_skill: dict[int, SkillScore] = {}
    for sid, raw in skill_raw.items():
        floored = max(raw, Decimal("0"))
        per_skill[sid] = SkillScore(
            skill_id=sid,
            score=floored,
            max=skill_max[sid],
            percentage=_pct(floored, skill_max[sid]),
            question_count=skill_count[sid],
        )
    return ScoreOutcome(
        total_score=total,
        max_score=max_total,
        percentage=_pct(total, max_total),
        per_skill=per_skill,
    )
