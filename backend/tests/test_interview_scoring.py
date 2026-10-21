"""Pure scoring tests for rubric-1."""
from app.services.interview_scoring import (
    DISCLAIMER,
    SCORING_VERSION,
    Concept,
    QuestionInput,
    keyword_in,
    score_interview,
    score_question,
)


def q(
    answer: str | None, *, qid: int = 1, pos: int = 1, comp: str = "Tech", min_words: int = 0,
    rubric: tuple[Concept, ...] | None = None,
) -> QuestionInput:
    rub = rubric if rubric is not None else (
        Concept("indexing", ("index", "b-tree"), 2.0),
        Concept("joins", ("inner join", "join"), 1.0),
    )
    return QuestionInput(qid, pos, f"Prompt {qid}", comp, min_words, rub, answer)


def test_keyword_case_and_word_boundary() -> None:
    assert keyword_in("Use an INDEX here", "index")
    assert not keyword_in("reindexing is costly", "index")
    assert not keyword_in("indexes", "index")
    assert keyword_in("an index.", "index")
    assert keyword_in("a b-tree structure", "b-tree")
    assert not keyword_in("anything", "   ")


def test_phrase_matching_flexible_whitespace() -> None:
    assert keyword_in("an Inner   Join works", "inner join")
    assert keyword_in("an inner\njoin works", "inner join")
    assert not keyword_in("inner outer join", "inner join")


def test_weighted_score_and_concepts() -> None:
    s = score_question(q("I would add an index"))
    assert s.score == 66.67 and s.answered
    assert s.covered_concepts == ["indexing"] and s.missed_concepts == ["joins"]
    full = score_question(q("index and join"))
    assert full.score == 100.0 and full.missed_concepts == []
    assert score_question(q("nothing relevant")).score == 0.0


def test_unanswered_and_blank() -> None:
    for text in (None, "", "   \n"):
        s = score_question(q(text, min_words=3))
        assert s.score == 0.0 and s.answered is False
        assert s.missed_concepts == ["indexing", "joins"] and s.covered_concepts == []
        assert s.too_short is True


def test_too_short_flag_does_not_change_score() -> None:
    short = score_question(q("index", min_words=5))
    long = score_question(q("index", min_words=1))
    assert short.too_short and not long.too_short
    assert short.score == long.score == 66.67


def test_competency_means_overall_and_rounding() -> None:
    qs = [
        q("index and join", qid=1, pos=1, comp="A"),
        q("index", qid=2, pos=2, comp="A"),
        q(None, qid=3, pos=3, comp="B"),
    ]
    out = score_interview(qs)
    comp = {c.competency: c for c in out.competencies}
    assert comp["A"].score == 83.34 and comp["A"].questions == 2
    assert comp["B"].score == 0.0
    assert out.overall == 55.56
    assert [s.position for s in out.questions] == [1, 2, 3]


def test_empty_interview_overall_none() -> None:
    out = score_interview([])
    assert out.overall is None and out.competencies == [] and out.questions == []


def test_zero_total_weight_scores_zero() -> None:
    assert score_question(q("x", rubric=())).score == 0.0


def test_deterministic_and_order_independent() -> None:
    qs = [q("index", qid=2, pos=2), q("join", qid=1, pos=1)]
    assert score_interview(qs) == score_interview(list(reversed(qs)))
    assert score_interview(qs) == score_interview(qs)


def test_constants() -> None:
    assert SCORING_VERSION == "rubric-1"
    assert "coverage of the configured concepts only" in DISCLAIMER
    assert "do not assess communication quality, confidence or personality" in DISCLAIMER
