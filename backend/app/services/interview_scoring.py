"""Deterministic keyword-rubric scoring for text mock interviews (pure, no I/O).

scoring_version: ``rubric-1``.

What it measures: coverage of the configured concepts only. A concept is covered when any of
its keywords occurs in the answer (case-insensitive, word-boundary-aware; multi-word phrases
allowed, internal whitespace is flexible). It does NOT assess communication quality,
confidence or personality.

Formulas (UNCONFIRMED policy assumptions, to be confirmed by the product owner):
- question score = sum(weights of covered concepts) / sum(all weights) * 100, rounded to 2dp;
  a blank/unanswered question scores 0 and ``answered`` is False.
- ``too_short`` (word_count < min_words) is a flag only and never changes the score.
- competency score = plain mean of its questions' scores (equal question weights).
- overall = plain mean of all question scores (None when there are no questions).
- Means are taken over the already-rounded (2dp) question scores, then rounded to 2dp.
"""
import re
from dataclasses import dataclass, field

SCORING_VERSION = "rubric-1"
DISCLAIMER = (
    "Scores measure coverage of the configured concepts only; they do not assess "
    "communication quality, confidence or personality."
)


@dataclass(frozen=True)
class Concept:
    """A rubric concept with its trigger keywords and weight."""

    concept: str
    keywords: tuple[str, ...]
    weight: float


@dataclass(frozen=True)
class QuestionInput:
    """One question with its answer to score."""

    question_id: int
    position: int
    prompt: str
    competency: str
    min_words: int
    rubric: tuple[Concept, ...]
    answer_text: str | None


@dataclass(frozen=True)
class QuestionScore:
    """Scored question."""

    question_id: int
    position: int
    prompt: str
    competency: str
    score: float
    answered: bool
    too_short: bool
    covered_concepts: list[str] = field(default_factory=list)
    missed_concepts: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CompetencyScore:
    """Mean score of a competency."""

    competency: str
    score: float
    questions: int


@dataclass(frozen=True)
class InterviewOutcome:
    """Full scoring outcome."""

    overall: float | None
    competencies: list[CompetencyScore]
    questions: list[QuestionScore]


def word_count(text: str) -> int:
    """Whitespace-separated word count."""
    return len(text.split())


def keyword_in(text: str, keyword: str) -> bool:
    """Case-insensitive, word-boundary-aware occurrence of a word or phrase."""
    parts = keyword.split()
    if not parts:
        return False
    pattern = r"(?<!\w)" + r"\s+".join(re.escape(p) for p in parts) + r"(?!\w)"
    return re.search(pattern, text, re.IGNORECASE) is not None


def score_question(q: QuestionInput) -> QuestionScore:
    """Score one question."""
    text = (q.answer_text or "").strip()
    answered = bool(text)
    covered: list[str] = []
    missed: list[str] = []
    total = sum(c.weight for c in q.rubric)
    got = 0.0
    for c in q.rubric:
        if answered and any(keyword_in(text, k) for k in c.keywords):
            covered.append(c.concept)
            got += c.weight
        else:
            missed.append(c.concept)
    score = round(got / total * 100, 2) if answered and total > 0 else 0.0
    return QuestionScore(
        question_id=q.question_id,
        position=q.position,
        prompt=q.prompt,
        competency=q.competency,
        score=score,
        answered=answered,
        too_short=word_count(text) < q.min_words,
        covered_concepts=covered,
        missed_concepts=missed,
    )


def score_interview(questions: list[QuestionInput]) -> InterviewOutcome:
    """Score all questions of an interview."""
    scored = [score_question(q) for q in sorted(questions, key=lambda x: x.position)]
    groups: dict[str, list[float]] = {}
    for s in scored:
        groups.setdefault(s.competency, []).append(s.score)
    competencies = [
        CompetencyScore(competency=c, score=round(sum(v) / len(v), 2), questions=len(v))
        for c, v in groups.items()
    ]
    overall = round(sum(s.score for s in scored) / len(scored), 2) if scored else None
    return InterviewOutcome(overall=overall, competencies=competencies, questions=scored)
