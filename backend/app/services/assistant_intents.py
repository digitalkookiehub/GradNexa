"""Deterministic, pure intent routing for assistant questions.

Precedence (first matching rule wins; documented and unit tested):

1. ``eligibility_for_job``  - eligible / eligibility / can I apply / criteria to apply
2. ``plan_status``          - my plan / roadmap / plan progress / learning plan status
3. ``skill_gaps``           - gap(s), missing/weak skills, what to improve / learn
4. ``readiness_for_role``   - ready / readiness / prepared / how close am I
5. ``profile_summary``      - my profile / CGPA / attendance / arrears / about me
6. ``knowledge_question``   - everything else (answered from approved knowledge passages)

The question text only selects an intent. It never selects the student, the tools' identity
arguments or any permission.
"""
import re

ELIGIBILITY = "eligibility_for_job"
PLAN = "plan_status"
GAPS = "skill_gaps"
READINESS = "readiness_for_role"
PROFILE = "profile_summary"
KNOWLEDGE = "knowledge_question"

INTENTS = (ELIGIBILITY, PLAN, GAPS, READINESS, PROFILE, KNOWLEDGE)

_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        ELIGIBILITY,
        re.compile(
            r"\b(eligib\w*|can i apply|may i apply|allowed to apply|criteria (to|for) apply\w*)\b"
        ),
    ),
    (
        PLAN,
        re.compile(
            r"\b(my|current|active)\s+(learning\s+|study\s+)?(plan|roadmap|progress)\b"
            r"|\b(plan|roadmap)\s+(status|progress)\b|\bprogress\s+(on|of|in)\s+(my\s+)?plan\b"
        ),
    ),
    (
        GAPS,
        re.compile(
            r"\b(gaps?|missing skills?|skills? (am i|i am) missing|weak(ness(es)?)?|lack\w*"
            r"|what (skills?|should i (learn|improve))|improve"
            r"|skills? to (learn|improve|work on))\b"
        ),
    ),
    (
        READINESS,
        re.compile(
            r"\b(ready|readiness|prepared|how close|am i fit|job[- ]ready|placement[- ]ready)\b"
        ),
    ),
    (
        PROFILE,
        re.compile(
            r"\b(my\s+(profile|cgpa|attendance|arrears|academic\w*|details|department|record)"
            r"|about me|summar(y|ise|ize) (of )?(me|my)|who am i)\b"
        ),
    ),
)


def classify(question: str) -> str:
    """Return the intent name for a question (pure function, case-insensitive)."""
    text = " ".join(question.lower().split())
    for name, pattern in _RULES:
        if pattern.search(text):
            return name
    return KNOWLEDGE


def mentions_name(question: str, names: list[tuple[int, str]]) -> int | None:
    """Id of the single name appearing as a whole phrase in the question, else None.

    Used only to pick a career role among the student's own visible roles. When several
    different names match, the longest one wins; ties are ambiguous and return None.
    """
    text = " ".join(question.lower().split())
    hits: list[tuple[int, int]] = []
    for ident, name in names:
        needle = " ".join(name.lower().split())
        if needle and re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", text):
            hits.append((len(needle), ident))
    if not hits:
        return None
    hits.sort(reverse=True)
    if len(hits) > 1 and hits[0][0] == hits[1][0]:
        return None
    return hits[0][1]
