"""Deterministic AI-assistant orchestrator (no LLM in this phase).

Flow: authenticated student -> student row from the principal (never from text) -> intent
routing -> read-only MCP tools -> stored deterministic results -> approved-knowledge retrieval
-> templated sections + citations -> audit (question LENGTH and intent only).

Nothing here invents facts: every number comes from a tool/service result, every knowledge
statement is a stored approved passage, and nothing is recomputed silently.
"""
import logging
from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.exceptions import ForbiddenError, NotFoundError
from app.mcp import registry
from app.mcp import schemas as ms
from app.mcp.tools import resolve_student
from app.models import Student, User
from app.schemas.assistant import (
    AnswerSection,
    AssistantQuery,
    AssistantResponse,
    Citation,
    Fact,
    IntentName,
)
from app.services import (
    assistant_intents,
    audit_service,
    career_goal_service,
    career_role_service,
    job_student_service,
    llm_provider,
    retrieval_service,
)

logger = logging.getLogger(__name__)

ASSISTANT_QUERY = "ASSISTANT_QUERY"
INSUFFICIENT_TEXT = "I don't have enough approved information to answer this confidently."
MAX_ROLE_CHOICES = 20
MAX_JOB_CHOICES = 10
MAX_GAPS_SHOWN = 5
TOP_K = 5

T = TypeVar("T", bound=BaseModel)


class _Ctx:
    """Mutable per-request state."""

    def __init__(self, db: Session, user: User, student: Student) -> None:
        self.db = db
        self.user = user
        self.student = student
        self.tools_used: list[str] = []
        self.notes: list[str] = [llm_provider.LLM_NOT_IMPLEMENTED_NOTE]
        self.citations: list[Citation] = []
        self.insufficient = False


def _call(ctx: _Ctx, name: str, arguments: dict[str, object], out: type[T]) -> T | None:
    """Run one MCP tool as the authenticated principal; None when the tool is disabled."""
    try:
        result = registry.call_tool(ctx.db, ctx.user, name, dict(arguments))
    except ForbiddenError as exc:
        if exc.detail == "Tool disabled":
            ctx.notes.append(f"The tool {name} is disabled for your college, so that part is "
                             "unavailable.")
            return None
        raise
    ctx.tools_used.append(name)
    return out.model_validate(result.model_dump())


def _fmt(value: float | None) -> str | float:
    return "not available" if value is None else round(value, 2)


# ---- retrieval -------------------------------------------------------------------------------
def _retrieve(ctx: _Ctx, query: str) -> AnswerSection | None:
    """Cited approved passages for a query, or None when evidence is insufficient."""
    res = retrieval_service.search(
        ctx.db,
        college_id=ctx.student.college_id,
        department_id=ctx.student.department_id,
        query=query,
        top_k=TOP_K,
    )
    if res.insufficient_evidence or not res.passages:
        return None
    lines: list[str] = []
    for n, p in enumerate(res.passages, start=1):
        ctx.citations.append(
            Citation(
                document_id=p.document_id,
                document_title=p.document_title,
                source_type=str(p.source_type),
                chunk_id=p.chunk_id,
                chunk_index=p.chunk_index,
                snippet=p.snippet,
            )
        )
        lines.append(f"[{n}] {p.snippet}")
    return AnswerSection(
        heading="Relevant approved guidance",
        text="\n".join(lines),
        facts=[
            Fact(label=f"[{n}] source", value=p.document_title)
            for n, p in enumerate(res.passages, start=1)
        ],
    )


# ---- role / job resolution -------------------------------------------------------------------
def _resolve_role(ctx: _Ctx, q: AssistantQuery) -> tuple[int, str] | list[tuple[int, str]]:
    """Role id and name, or the list of choices when none can be decided.

    Order: explicit role_id (validated) > a visible role name in the question > top goal.
    """
    if q.role_id is not None:
        role = career_role_service.get_visible_role(ctx.db, ctx.student, q.role_id)
        return role.id, role.name
    roles = career_goal_service.list_roles_for_student(ctx.db, ctx.student)
    named = assistant_intents.mentions_name(q.question, [(r.id, r.name) for r in roles])
    if named is not None:
        return named, next(r.name for r in roles if r.id == named)
    goals = career_goal_service.list_goals(ctx.db, ctx.student)
    if goals:
        return goals[0].career_role_id, goals[0].role_name
    return [(r.id, r.name) for r in roles[:MAX_ROLE_CHOICES]]


def _choose_role_section(choices: list[tuple[int, str]]) -> AnswerSection:
    if not choices:
        return AnswerSection(
            heading="Choose a career role",
            text="There are no career roles available to you yet. Ask your placement office "
            "to publish roles for your department.",
        )
    return AnswerSection(
        heading="Choose a career role",
        text="Tell me which career role to check (send its role_id), or set a career goal. "
        "Available roles are listed below.",
        facts=[Fact(label=f"role_id {i}", value=n) for i, n in choices],
    )


# ---- section builders ------------------------------------------------------------------------
def _readiness_section(role_name: str, summary: ms.ReadinessSummary | None) -> AnswerSection:
    heading = f"Current readiness for {role_name}"
    if summary is None:
        return AnswerSection(
            heading=heading,
            text=f"Your readiness for {role_name} has not been computed yet. Compute it from "
            "the Readiness page (/readiness) to see your current readiness level.",
        )
    return AnswerSection(
        heading=heading,
        text=f"Your current readiness level for {role_name} is "
        f"{summary.level or 'not available'}, from your latest stored result.",
        facts=[
            Fact(label="Overall score", value=_fmt(summary.overall)),
            Fact(label="Current readiness level", value=summary.level),
            Fact(label="Coverage", value=_fmt(summary.coverage)),
            Fact(label="Rule version", value=summary.rule_version),
            Fact(label="Computed at", value=summary.computed_at.isoformat()),
        ],
    )


def _gaps_section(
    role_name: str, summary: ms.ReadinessSummary | None, limit: int
) -> AnswerSection:
    heading = f"Top skill gaps for {role_name}"
    if summary is None:
        return AnswerSection(
            heading=heading,
            text="No stored gap analysis exists yet because readiness has not been computed. "
            "Compute it from the Readiness page (/readiness) first.",
        )
    gaps = [g for g in summary.gaps if g.status == "GAP"][:limit]
    if not gaps:
        return AnswerSection(
            heading=heading, text="Your latest stored result lists no skill gaps for this role."
        )
    return AnswerSection(
        heading=heading,
        text="Gaps from your latest stored result, highest priority first.",
        facts=[
            Fact(
                label=g.skill_name,
                value=f"{g.priority} priority: current {_fmt(g.current)} of required "
                f"{_fmt(g.required)}. {g.recommended_action}",
            )
            for g in gaps
        ],
    )


def _plan_section(progress: ms.ProgressOut | None) -> AnswerSection:
    if progress is None:
        return AnswerSection(
            heading="Learning plan", text="Learning plan information is unavailable."
        )
    plan = progress.plan
    if plan is None:
        return AnswerSection(
            heading="Learning plan",
            text="You do not have an active learning plan. Generate one from the Learning Plan "
            "page after computing readiness for a role.",
        )
    return AnswerSection(
        heading="Learning plan",
        text=f"Your active plan for {plan.role_name} has {plan.done} of {plan.total} items "
        "completed.",
        facts=[
            Fact(label="Role", value=plan.role_name),
            Fact(label="Status", value=plan.status),
            Fact(label="Items done", value=plan.done),
            Fact(label="Items total", value=plan.total),
            Fact(label="Percent complete", value=plan.percent),
            Fact(label="Starts on", value=plan.starts_on.isoformat()),
        ],
    )


# ---- intent handlers -------------------------------------------------------------------------
def _readiness(ctx: _Ctx, q: AssistantQuery, with_gaps_only: bool) -> list[AnswerSection]:
    choice = _resolve_role(ctx, q)
    if isinstance(choice, list):
        return [_choose_role_section(choice)]
    role_id, role_name = choice
    progress = _call(ctx, "get_student_progress", {"role_id": role_id}, ms.ProgressOut)
    summary = progress.latest_readiness if progress is not None else None
    sections: list[AnswerSection] = []
    if not with_gaps_only:
        sections.append(_readiness_section(role_name, summary))
    sections.append(_gaps_section(role_name, summary, MAX_GAPS_SHOWN if not with_gaps_only else 10))
    guidance = _retrieve(ctx, f"{q.question} {role_name}")
    if guidance is not None:
        sections.append(guidance)
    return sections


def _eligibility(ctx: _Ctx, q: AssistantQuery) -> list[AnswerSection]:
    if q.job_id is None:
        jobs = job_student_service.list_jobs(ctx.db, ctx.student)[:MAX_JOB_CHOICES]
        return [
            AnswerSection(
                heading="Choose a job",
                text="Tell me which job to check (send its job_id). Open jobs are listed below."
                if jobs
                else "There are no open jobs to check right now.",
                facts=[Fact(label=f"job_id {j.id}", value=f"{j.title} ({j.company_name})")
                       for j in jobs],
            )
        ]
    job = _call(ctx, "get_job_description", {"job_id": q.job_id}, ms.JobDescriptionOut)
    elig = _call(ctx, "get_eligibility_rules", {"job_id": q.job_id}, ms.EligibilityRulesOut)
    sections: list[AnswerSection] = []
    if job is not None:
        sections.append(
            AnswerSection(
                heading="Job",
                text=f"{job.title} at {job.company.name}.",
                facts=[
                    Fact(label="Application deadline",
                         value=job.application_deadline.isoformat()
                         if job.application_deadline else None),
                    Fact(label="Required skills",
                         value=", ".join(s.skill_name for s in job.skills) or "none listed"),
                ],
            )
        )
    if elig is not None:
        ev = elig.evaluation
        if ev is None:
            sections.append(
                AnswerSection(
                    heading="Eligibility (configured criteria only)",
                    text="Eligibility could not be evaluated for this job.",
                )
            )
        else:
            sections.append(
                AnswerSection(
                    heading="Eligibility (configured criteria only)",
                    text=f"Eligibility status: {ev.status}. {ev.note}",
                    facts=[
                        Fact(label=c.label, value=f"{c.result} (required {c.required}, "
                             f"yours {c.actual if c.actual is not None else 'unknown'})")
                        for c in ev.criteria
                    ],
                )
            )
    ctx.notes.append("Eligibility is a separate check and is not combined with readiness.")
    return sections


def _plan(ctx: _Ctx) -> list[AnswerSection]:
    progress = _call(ctx, "get_student_progress", {}, ms.ProgressOut)
    sections = [_plan_section(progress)]
    if progress is not None and progress.latest_readiness is not None:
        r = progress.latest_readiness
        sections.append(_readiness_section(r.role_name or "general readiness", r))
    return sections


def _profile(ctx: _Ctx) -> list[AnswerSection]:
    sections: list[AnswerSection] = []
    prof = _call(ctx, "get_student_profile", {}, ms.ProfileOut)
    if prof is not None:
        sections.append(
            AnswerSection(
                heading="Profile",
                text=f"Profile summary for {prof.full_name}.",
                facts=[
                    Fact(label="Department", value=prof.department_name),
                    Fact(label="Roll number", value=prof.roll_number),
                    Fact(label="Graduation year", value=prof.graduation_year),
                    Fact(label="Profile complete", value=prof.profile_complete),
                ],
            )
        )
    acad = _call(ctx, "get_student_academic_record", {}, ms.AcademicRecordOut)
    if acad is not None:
        sections.append(
            AnswerSection(
                heading="Academic record",
                text="Latest stored academic record." if acad.records
                else "No academic records have been added yet.",
                facts=[
                    Fact(label="Latest semester", value=acad.latest_semester),
                    Fact(label="Latest CGPA", value=acad.latest_cgpa),
                    Fact(label="Latest attendance (%)", value=acad.latest_attendance_pct),
                    Fact(label="Semesters recorded", value=len(acad.records)),
                ],
            )
        )
    progress = _call(ctx, "get_student_progress", {}, ms.ProgressOut)
    sections.append(_plan_section(progress))
    return sections


def _knowledge(ctx: _Ctx, q: AssistantQuery) -> list[AnswerSection]:
    section = _retrieve(ctx, q.question)
    if section is None:
        ctx.insufficient = True
        return [AnswerSection(heading="Answer", text=INSUFFICIENT_TEXT)]
    section.heading = "Approved information"
    return [section]


def answer(db: Session, user: User, q: AssistantQuery) -> AssistantResponse:
    """Answer a student question deterministically (identity always from ``user``)."""
    student = resolve_student(db, user, None)
    ctx = _Ctx(db, user, student)
    intent = assistant_intents.classify(q.question)
    if intent == assistant_intents.READINESS:
        sections = _readiness(ctx, q, with_gaps_only=False)
    elif intent == assistant_intents.GAPS:
        sections = _readiness(ctx, q, with_gaps_only=True)
    elif intent == assistant_intents.ELIGIBILITY:
        sections = _eligibility(ctx, q)
    elif intent == assistant_intents.PLAN:
        sections = _plan(ctx)
    elif intent == assistant_intents.PROFILE:
        sections = _profile(ctx)
    else:
        sections = _knowledge(ctx, q)
    audit_service.record(
        db,
        ASSISTANT_QUERY,
        "assistant",
        user_id=user.id,
        college_id=user.college_id,
        metadata={
            "question_length": len(q.question),
            "intent": intent,
            "tools": sorted(set(ctx.tools_used)),
        },
    )
    db.commit()
    intent_name: IntentName = intent  # type: ignore[assignment]
    return AssistantResponse(
        question=q.question,
        answer_sections=sections,
        citations=ctx.citations,
        tools_used=list(dict.fromkeys(ctx.tools_used)),
        intent=intent_name,
        insufficient_evidence=ctx.insufficient,
        notes=ctx.notes,
    )


__all__ = ["answer", "INSUFFICIENT_TEXT", "NotFoundError"]
