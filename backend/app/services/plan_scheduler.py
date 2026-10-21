"""Deterministic 30-day learning plan scheduler (pure function, no I/O, no LLM).

Inputs are the stored skill gaps of a role and the ADMIN-APPROVED learning resources per skill.
Nothing is invented: a skill without an approved resource says so in its task text and carries
no resource.

Scheduling rules (all of these except ``skills_per_week`` are documented ASSUMPTIONS, not
institutional policy):

* The plan spans 4 weeks. Weeks 1-3 hold learning work; week 4 holds exactly one REASSESS item.
* NO_EVIDENCE skills get one ASSESS item each in week 1 ("Take an assessment that covers X").
  They are ordered by skill name and do NOT count toward ``skills_per_week``.
* GAP skills are ordered by priority (HIGH, MEDIUM, LOW), then larger gap first, then skill
  name, then skill id. ``skills_per_week`` skills are assigned to each of weeks 1, 2 and 3 in
  that order. Skills beyond ``3 * skills_per_week`` are returned as ``unscheduled``.
* Each scheduled skill yields up to ``MAX_RESOURCES_PER_SKILL`` (2) LEARN items (approved
  resources ordered by id) followed by one PRACTICE item built from the gap's recommended
  action. Within a week, ASSESS items come first, then skills in schedule order.
* READY skills are never scheduled.
"""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

KIND_LEARN = "LEARN"
KIND_PRACTICE = "PRACTICE"
KIND_ASSESS = "ASSESS"
KIND_REASSESS = "REASSESS"

STATUS_GAP = "GAP"
STATUS_NO_EVIDENCE = "NO_EVIDENCE"

LEARNING_WEEKS = (1, 2, 3)
REASSESS_WEEK = 4
MAX_RESOURCES_PER_SKILL = 2
DURATION_DAYS = 30
REASSESS_TASK = "Retake relevant assessments and refresh your readiness"
NO_RESOURCE_SUFFIX = " (no approved learning resource configured yet)"
_PRIORITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


@dataclass(frozen=True)
class GapInput:
    """A stored skill gap relevant to scheduling."""

    skill_id: int
    skill_name: str
    status: str
    priority: str
    gap: float | None
    recommended_action: str


@dataclass(frozen=True)
class ResourceInput:
    """An approved learning resource."""

    id: int
    title: str


@dataclass(frozen=True)
class ItemSpec:
    """One scheduled plan item."""

    week: int
    position: int
    kind: str
    skill_id: int | None
    resource_id: int | None
    task: str


@dataclass(frozen=True)
class Schedule:
    """Scheduling result."""

    items: list[ItemSpec]
    unscheduled: list[GapInput]


def gap_sort_key(g: GapInput) -> tuple[int, float, str, int]:
    """Sort key: priority HIGH>MEDIUM>LOW, larger gap first, then name, then id."""
    return (_PRIORITY_RANK.get(g.priority, 3), -(g.gap or 0.0), g.skill_name, g.skill_id)


def build_schedule(
    gaps: Sequence[GapInput],
    resources: Mapping[int, Sequence[ResourceInput]],
    skills_per_week: int,
) -> Schedule:
    """Build the plan items for the given gaps; identical inputs give identical output."""
    no_evidence = sorted(
        (g for g in gaps if g.status == STATUS_NO_EVIDENCE),
        key=lambda g: (g.skill_name, g.skill_id),
    )
    gap_skills = sorted((g for g in gaps if g.status == STATUS_GAP), key=gap_sort_key)
    capacity = skills_per_week * len(LEARNING_WEEKS)
    scheduled, unscheduled = gap_skills[:capacity], gap_skills[capacity:]

    # (week, kind, skill_id, resource_id, task) in order; positions are assigned per week after.
    drafts: list[tuple[int, str, int | None, int | None, str]] = []
    for g in no_evidence:
        drafts.append(
            (1, KIND_ASSESS, g.skill_id, None, f"Take an assessment that covers {g.skill_name}")
        )
    for index, g in enumerate(scheduled):
        week = LEARNING_WEEKS[index // skills_per_week]
        approved = sorted(resources.get(g.skill_id, ()), key=lambda r: r.id)[
            :MAX_RESOURCES_PER_SKILL
        ]
        for res in approved:
            drafts.append((week, KIND_LEARN, g.skill_id, res.id, f"Study: {res.title}"))
        task = f"Practise {g.skill_name}: {g.recommended_action}"
        if not approved:
            task += NO_RESOURCE_SUFFIX
        drafts.append((week, KIND_PRACTICE, g.skill_id, None, task))
    drafts.append((REASSESS_WEEK, KIND_REASSESS, None, None, REASSESS_TASK))

    counters: dict[int, int] = {}
    items: list[ItemSpec] = []
    for week, kind, skill_id, resource_id, task in drafts:
        counters[week] = counters.get(week, 0) + 1
        items.append(ItemSpec(week, counters[week], kind, skill_id, resource_id, task))
    return Schedule(items=items, unscheduled=unscheduled)
