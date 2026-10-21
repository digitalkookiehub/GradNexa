"""Learning plan generation, progress and reassessment (tenant scoped, deterministic).

Plans are produced by ``plan_scheduler.build_schedule`` from the stored skill gaps of the
student's latest role readiness and ADMIN-APPROVED learning resources only. A resource that is
unapproved (or deleted) after plan creation is no longer shown on its plan item.
"""
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.models import (
    LearningPlan,
    LearningPlanItem,
    LearningResource,
    PlanItemKind,
    PlanItemStatus,
    PlanStatus,
    ReadinessScore,
    Skill,
    SkillGap,
    Student,
    User,
)
from app.schemas.planning import (
    ItemResource,
    PlanBaseline,
    PlanItemResponse,
    PlanResponse,
    PlanSummary,
    PlanWeek,
    Progress,
    ReassessBaseline,
    ReassessResponse,
    SkillChange,
    UnscheduledSkill,
)
from app.services import audit_service, career_role_service, plan_scheduler, readiness_service
from app.services.plan_scheduler import GapInput, ResourceInput

PLAN_GENERATE = "LEARNING_PLAN_GENERATE"
PLAN_ITEM_STATUS = "LEARNING_PLAN_ITEM_STATUS"
PLAN_REASSESS = "LEARNING_PLAN_REASSESS"
WEEK_NUMBERS = (1, 2, 3, 4)


# ---- helpers ------------------------------------------------------------------------------
def _latest_role_score(db: Session, student: Student, role_id: int) -> ReadinessScore | None:
    return db.execute(
        select(ReadinessScore)
        .where(
            ReadinessScore.student_id == student.id,
            ReadinessScore.college_id == student.college_id,
            ReadinessScore.role_id == role_id,
        )
        .order_by(ReadinessScore.computed_at.desc(), ReadinessScore.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def _gap_rows(db: Session, college_id: int, score_id: int) -> list[tuple[SkillGap, str]]:
    stmt = (
        select(SkillGap, Skill.name)
        .join(Skill, Skill.id == SkillGap.skill_id)
        .where(
            SkillGap.readiness_score_id == score_id,
            SkillGap.college_id == college_id,
            Skill.college_id == college_id,
        )
        .order_by(SkillGap.id)
    )
    return [(g, n) for g, n in db.execute(stmt).all()]


def _approved_resources(
    db: Session, college_id: int, skill_ids: list[int]
) -> dict[int, list[ResourceInput]]:
    result: dict[int, list[ResourceInput]] = {}
    if not skill_ids:
        return result
    stmt = (
        select(LearningResource.id, LearningResource.skill_id, LearningResource.title)
        .where(
            LearningResource.college_id == college_id,
            LearningResource.is_approved.is_(True),
            LearningResource.skill_id.in_(skill_ids),
        )
        .order_by(LearningResource.id)
    )
    for rid, sid, title in db.execute(stmt).all():
        result.setdefault(int(sid), []).append(ResourceInput(id=int(rid), title=str(title)))
    return result


def _progress_for(db: Session, college_id: int, plan_ids: list[int]) -> dict[int, Progress]:
    out: dict[int, Progress] = {pid: Progress(done=0, total=0, percent=0.0) for pid in plan_ids}
    if not plan_ids:
        return out
    stmt = (
        select(LearningPlanItem.plan_id, LearningPlanItem.status, func.count(LearningPlanItem.id))
        .where(LearningPlanItem.plan_id.in_(plan_ids), LearningPlanItem.college_id == college_id)
        .group_by(LearningPlanItem.plan_id, LearningPlanItem.status)
    )
    totals: dict[int, int] = {}
    done: dict[int, int] = {}
    for pid, status, count in db.execute(stmt).all():
        totals[pid] = totals.get(pid, 0) + int(count)
        if status == PlanItemStatus.DONE:
            done[pid] = int(count)
    for pid in plan_ids:
        total, d = totals.get(pid, 0), done.get(pid, 0)
        percent = round(d / total * 100, 1) if total else 0.0
        out[pid] = Progress(done=d, total=total, percent=percent)
    return out


def _item_response(
    item: LearningPlanItem, skill_name: str | None, res: LearningResource | None
) -> PlanItemResponse:
    resource = None
    if res is not None and res.is_approved:
        resource = ItemResource(id=res.id, title=res.title, url=res.url)
    return PlanItemResponse(
        id=item.id,
        week=item.week,
        position=item.position,
        kind=item.kind,
        skill_id=item.skill_id,
        skill_name=skill_name,
        resource=resource,
        task=item.task,
        status=item.status,
        completed_at=item.completed_at,
    )


def _items(db: Session, plan: LearningPlan) -> list[PlanItemResponse]:
    stmt = (
        select(LearningPlanItem, Skill.name, LearningResource)
        .outerjoin(Skill, Skill.id == LearningPlanItem.skill_id)
        .outerjoin(LearningResource, LearningResource.id == LearningPlanItem.resource_id)
        .where(
            LearningPlanItem.plan_id == plan.id,
            LearningPlanItem.college_id == plan.college_id,
        )
        .order_by(LearningPlanItem.week, LearningPlanItem.position, LearningPlanItem.id)
    )
    out: list[PlanItemResponse] = []
    for item, sname, res in db.execute(stmt).all():
        if res is not None and res.college_id != plan.college_id:
            res = None
        out.append(_item_response(item, sname, res))
    return out


def _role_name(db: Session, college_id: int, role_id: int) -> str:
    return career_role_service.get_role(db, college_id, role_id).name


def _baseline(db: Session, plan: LearningPlan) -> tuple[ReadinessScore | None, PlanBaseline | None]:
    if plan.baseline_readiness_score_id is None:
        return None, None
    score = db.execute(
        select(ReadinessScore).where(
            ReadinessScore.id == plan.baseline_readiness_score_id,
            ReadinessScore.college_id == plan.college_id,
        )
    ).scalar_one_or_none()
    if score is None:
        return None, None
    return score, PlanBaseline(
        readiness_score_id=score.id,
        overall=float(score.overall) if score.overall is not None else None,
        level=score.level,
        rule_version=score.rule_version,
        computed_at=score.computed_at,
    )


def to_response(db: Session, plan: LearningPlan) -> PlanResponse:
    """Full API representation of a plan."""
    items = _items(db, plan)
    weeks = [PlanWeek(week=w, items=[i for i in items if i.week == w]) for w in WEEK_NUMBERS]
    score, baseline = _baseline(db, plan)
    planned = {i.skill_id for i in items if i.skill_id is not None}
    unscheduled: list[UnscheduledSkill] = []
    if score is not None:
        gaps = [
            GapInput(
                g.skill_id, name, g.status.value, g.priority.value,
                float(g.gap) if g.gap is not None else None, g.recommended_action,
            )
            for g, name in _gap_rows(db, plan.college_id, score.id)
            if g.status.value == plan_scheduler.STATUS_GAP and g.skill_id not in planned
        ]
        unscheduled = [
            UnscheduledSkill(skill_id=g.skill_id, skill_name=g.skill_name, gap=g.gap)
            for g in sorted(gaps, key=plan_scheduler.gap_sort_key)
        ]
    return PlanResponse(
        id=plan.id,
        role_id=plan.role_id,
        role_name=_role_name(db, plan.college_id, plan.role_id),
        status=plan.status,
        starts_on=plan.starts_on,
        duration_days=plan.duration_days,
        skills_per_week=plan.skills_per_week,
        baseline=baseline,
        weeks=weeks,
        unscheduled_skills=unscheduled,
        progress=_progress_for(db, plan.college_id, [plan.id])[plan.id],
    )


def _active_plan(db: Session, student: Student) -> LearningPlan | None:
    return db.execute(
        select(LearningPlan)
        .where(
            LearningPlan.student_id == student.id,
            LearningPlan.college_id == student.college_id,
            LearningPlan.status == PlanStatus.ACTIVE,
        )
        .order_by(LearningPlan.id.desc())
        .limit(1)
    ).scalar_one_or_none()


# ---- operations ---------------------------------------------------------------------------
def generate(
    db: Session, user: User, student: Student, role_id: int, skills_per_week: int
) -> PlanResponse:
    """Generate a plan from the latest stored gaps of ``role_id`` (409 when none exist)."""
    role = career_role_service.get_visible_role(db, student, role_id)
    score = _latest_role_score(db, student, role.id)
    if score is None:
        raise ConflictError("Compute readiness for this role first")
    rows = _gap_rows(db, student.college_id, score.id)
    gaps = [
        GapInput(
            g.skill_id, name, g.status.value, g.priority.value,
            float(g.gap) if g.gap is not None else None, g.recommended_action,
        )
        for g, name in rows
    ]
    resources = _approved_resources(
        db, student.college_id, [g.skill_id for g in gaps if g.status == plan_scheduler.STATUS_GAP]
    )
    schedule = plan_scheduler.build_schedule(gaps, resources, skills_per_week)

    for old in db.execute(
        select(LearningPlan).where(
            LearningPlan.student_id == student.id,
            LearningPlan.college_id == student.college_id,
            LearningPlan.status == PlanStatus.ACTIVE,
        )
    ).scalars():
        old.status = PlanStatus.ARCHIVED
    plan = LearningPlan(
        student_id=student.id,
        college_id=student.college_id,
        role_id=role.id,
        baseline_readiness_score_id=score.id,
        status=PlanStatus.ACTIVE,
        starts_on=datetime.now(UTC).date(),
        duration_days=plan_scheduler.DURATION_DAYS,
        skills_per_week=skills_per_week,
    )
    db.add(plan)
    db.flush()
    for spec in schedule.items:
        db.add(
            LearningPlanItem(
                plan_id=plan.id,
                college_id=student.college_id,
                week=spec.week,
                position=spec.position,
                kind=PlanItemKind(spec.kind),
                skill_id=spec.skill_id,
                resource_id=spec.resource_id,
                task=spec.task,
                status=PlanItemStatus.TODO,
            )
        )
    audit_service.record(
        db,
        PLAN_GENERATE,
        "learning_plan",
        user_id=user.id,
        college_id=user.college_id,
        resource_id=plan.id,
        metadata={
            "role_id": role.id,
            "skills_per_week": skills_per_week,
            "baseline_readiness_score_id": score.id,
            "item_count": len(schedule.items),
        },
    )
    db.commit()
    return to_response(db, plan)


def get_active(db: Session, student: Student) -> PlanResponse:
    """The student's ACTIVE plan or NotFoundError."""
    plan = _active_plan(db, student)
    if plan is None:
        raise NotFoundError("No active learning plan")
    return to_response(db, plan)


def history(db: Session, student: Student) -> list[PlanSummary]:
    """All of the student's plans, newest first."""
    plans = list(
        db.execute(
            select(LearningPlan)
            .where(
                LearningPlan.student_id == student.id,
                LearningPlan.college_id == student.college_id,
            )
            .order_by(LearningPlan.id.desc())
        ).scalars()
    )
    progress = _progress_for(db, student.college_id, [p.id for p in plans])
    return [
        PlanSummary(
            id=p.id,
            role_id=p.role_id,
            role_name=_role_name(db, p.college_id, p.role_id),
            status=p.status,
            starts_on=p.starts_on,
            progress=progress[p.id],
        )
        for p in plans
    ]


def update_item_status(
    db: Session, user: User, student: Student, item_id: int, status: PlanItemStatus
) -> PlanItemResponse:
    """Set an own item's status; keeps completed_at and the plan status consistent."""
    row = db.execute(
        select(LearningPlanItem, LearningPlan)
        .join(LearningPlan, LearningPlan.id == LearningPlanItem.plan_id)
        .where(
            LearningPlanItem.id == item_id,
            LearningPlanItem.college_id == student.college_id,
            LearningPlan.student_id == student.id,
            LearningPlan.college_id == student.college_id,
        )
    ).first()
    if row is None:
        raise NotFoundError("Plan item not found")
    item, plan = row
    previous = item.status
    item.status = status
    item.completed_at = datetime.now(UTC) if status == PlanItemStatus.DONE else None
    db.flush()
    remaining = db.execute(
        select(func.count(LearningPlanItem.id)).where(
            LearningPlanItem.plan_id == plan.id,
            LearningPlanItem.college_id == plan.college_id,
            LearningPlanItem.status != PlanItemStatus.DONE,
        )
    ).scalar_one()
    if plan.status == PlanStatus.ACTIVE and remaining == 0:
        plan.status = PlanStatus.COMPLETED
    elif plan.status == PlanStatus.COMPLETED and remaining > 0:
        plan.status = PlanStatus.ACTIVE
    audit_service.record(
        db,
        PLAN_ITEM_STATUS,
        "learning_plan_item",
        user_id=user.id,
        college_id=user.college_id,
        resource_id=item.id,
        metadata={"plan_id": plan.id, "from": previous.value, "to": status.value},
    )
    db.commit()
    for resp in _items(db, plan):
        if resp.id == item.id:
            return resp
    raise NotFoundError("Plan item not found")  # pragma: no cover


def _evidence_scores(evidence: list[dict[str, object]]) -> dict[int, tuple[str, float]]:
    return {
        int(str(e["skill_id"])): (str(e["skill_name"]), float(str(e["score"]))) for e in evidence
    }


def reassess(db: Session, user: User, student: Student) -> ReassessResponse:
    """Recompute readiness for the active plan's role and compare with the plan baseline."""
    plan = _active_plan(db, student)
    if plan is None:
        raise NotFoundError("No active learning plan")
    baseline_score, _ = _baseline(db, plan)
    current = readiness_service.compute(db, user, student, plan.role_id)

    before: dict[int, tuple[str, float]] = {}
    names: dict[int, str] = {}
    if baseline_score is not None:
        before = _evidence_scores(list(baseline_score.evidence))
        for g, name in _gap_rows(db, plan.college_id, baseline_score.id):
            names[g.skill_id] = name
    after = _evidence_scores([e.model_dump() for e in current.evidence])
    for cg in current.gaps:
        names[cg.skill_id] = cg.skill_name
    for sid, (name, _) in {**before, **after}.items():
        names.setdefault(sid, name)

    changes: list[SkillChange] = []
    for sid in sorted(names, key=lambda i: (names[i], i)):
        b = before[sid][1] if sid in before else None
        a = after[sid][1] if sid in after else None
        delta = round(a - b, 2) if a is not None and b is not None else None
        changes.append(
            SkillChange(skill_id=sid, skill_name=names[sid], before=b, after=a, delta=delta)
        )

    base_overall: float | None = None
    if baseline_score is not None and baseline_score.overall is not None:
        base_overall = float(baseline_score.overall)
    delta_overall = (
        round(current.overall - base_overall, 2)
        if current.overall is not None and base_overall is not None
        else None
    )
    audit_service.record(
        db,
        PLAN_REASSESS,
        "learning_plan",
        user_id=user.id,
        college_id=user.college_id,
        resource_id=plan.id,
        metadata={"readiness_score_id": current.id, "overall_delta": delta_overall},
    )
    db.commit()
    return ReassessResponse(
        plan_id=plan.id,
        baseline=ReassessBaseline(
            overall=base_overall,
            level=baseline_score.level,
            rule_version=baseline_score.rule_version,
        )
        if baseline_score is not None
        else None,
        current=current,
        overall_delta=delta_overall,
        rule_version_changed=baseline_score is not None
        and baseline_score.rule_version != current.rule_version,
        skill_changes=changes,
    )

