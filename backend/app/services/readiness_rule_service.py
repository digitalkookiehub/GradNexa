"""Readiness rule versioning (admin only, tenant scoped). Rules are immutable once created."""
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, UnprocessableError
from app.models import ReadinessRule, SkillCategory
from app.schemas.readiness import ReadinessRuleCreate, ReadinessRuleResponse
from app.services import audit_service


def to_response(rule: ReadinessRule) -> ReadinessRuleResponse:
    """Convert a stored rule to its response schema."""
    return ReadinessRuleResponse.model_validate(
        {
            "id": rule.id,
            "version": rule.version,
            "is_active": rule.is_active,
            "weights": rule.weights,
            "level_thresholds": rule.level_thresholds,
            "gap_thresholds": rule.gap_thresholds,
            "created_by": rule.created_by,
            "created_at": rule.created_at,
        }
    )


def list_rules(db: Session, college_id: int) -> list[ReadinessRule]:
    """All rule versions of the college, newest first."""
    stmt = (
        select(ReadinessRule)
        .where(ReadinessRule.college_id == college_id)
        .order_by(ReadinessRule.version.desc())
    )
    return list(db.execute(stmt).scalars())


def get_rule(db: Session, college_id: int, rule_id: int) -> ReadinessRule:
    """Fetch a rule of the college or raise NotFoundError."""
    rule = db.execute(
        select(ReadinessRule).where(
            ReadinessRule.id == rule_id, ReadinessRule.college_id == college_id
        )
    ).scalar_one_or_none()
    if rule is None:
        raise NotFoundError("Readiness rule not found")
    return rule


def get_active_rule(db: Session, college_id: int) -> ReadinessRule | None:
    """The single active rule of the college, if any."""
    return db.execute(
        select(ReadinessRule).where(
            ReadinessRule.college_id == college_id, ReadinessRule.is_active.is_(True)
        )
    ).scalar_one_or_none()


def _validate(db: Session, college_id: int, data: ReadinessRuleCreate) -> None:
    """Semantic validation; raises UnprocessableError."""
    if not data.weights:
        raise UnprocessableError("weights must contain at least one skill category")
    category_ids: set[int] = set()
    for key, weight in data.weights.items():
        try:
            category_ids.add(int(key))
        except ValueError as exc:
            raise UnprocessableError(f"weights key '{key}' is not a skill category id") from exc
        if weight <= 0:
            raise UnprocessableError("weights must be greater than 0")
    found = set(
        db.execute(
            select(SkillCategory.id).where(
                SkillCategory.college_id == college_id, SkillCategory.id.in_(category_ids)
            )
        ).scalars()
    )
    if found != category_ids:
        raise UnprocessableError("weights reference unknown skill categories")
    if not data.level_thresholds:
        raise UnprocessableError("at least one level threshold is required")
    names = [t.level.strip() for t in data.level_thresholds]
    if any(not n for n in names) or len(set(names)) != len(names):
        raise UnprocessableError("level names must be non-empty and unique")
    gaps = data.gap_thresholds
    if not 0 < gaps.medium_min_gap <= gaps.high_min_gap <= 100:
        raise UnprocessableError("gap thresholds require 0 < medium_min_gap <= high_min_gap <= 100")


def create_rule(
    db: Session, college_id: int, actor_id: int, data: ReadinessRuleCreate
) -> ReadinessRule:
    """Create the next rule version (inactive)."""
    _validate(db, college_id, data)
    latest = db.execute(
        select(func.max(ReadinessRule.version)).where(ReadinessRule.college_id == college_id)
    ).scalar_one()
    rule = ReadinessRule(
        college_id=college_id,
        version=(latest or 0) + 1,
        weights={str(int(k)): float(v) for k, v in data.weights.items()},
        level_thresholds=[
            {"level": t.level.strip(), "min_score": float(t.min_score)}
            for t in data.level_thresholds
        ],
        gap_thresholds={
            "high_min_gap": float(data.gap_thresholds.high_min_gap),
            "medium_min_gap": float(data.gap_thresholds.medium_min_gap),
        },
        is_active=False,
        created_by=actor_id,
    )
    db.add(rule)
    db.flush()
    audit_service.record(
        db,
        "READINESS_RULE_CREATE",
        "readiness_rule",
        user_id=actor_id,
        college_id=college_id,
        resource_id=rule.id,
        metadata={"version": rule.version},
    )
    db.commit()
    return rule


def activate_rule(db: Session, college_id: int, actor_id: int, rule_id: int) -> ReadinessRule:
    """Make a rule the single active one of the college (deactivating the previous)."""
    rule = get_rule(db, college_id, rule_id)
    if not rule.is_active:
        db.execute(
            update(ReadinessRule)
            .where(ReadinessRule.college_id == college_id, ReadinessRule.is_active.is_(True))
            .values(is_active=False)
        )
        rule.is_active = True
        audit_service.record(
            db,
            "READINESS_RULE_ACTIVATE",
            "readiness_rule",
            user_id=actor_id,
            college_id=college_id,
            resource_id=rule.id,
            metadata={"version": rule.version},
        )
        db.commit()
    return rule
