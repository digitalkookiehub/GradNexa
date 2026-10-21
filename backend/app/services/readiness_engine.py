"""Pure, deterministic readiness and skill-gap engine (no I/O, no LLM, no randomness).

Scope of this phase: ONLY assessment-derived skill evidence (StudentSkill scores) feeds the
score. Resume, interview, projects and academic components are NOT implemented in this phase.
Eligibility is a separate concept and is never part of readiness.

No default weights or thresholds exist in this module: every weight, level threshold and gap
threshold is supplied by the caller from an admin-created, versioned institutional rule.

ASSUMPTIONS (institutional policy is unknown; these aggregation choices are documented, not
mandated by the product owner):
1. A StudentSkill row is the evidence for a skill; skills without a row have no evidence.
2. A category score is the plain (unweighted) mean of the student's scores for the evidenced
   skills in that category.
3. Categories (general score) or skills (role score) without evidence are EXCLUDED from the
   weighted mean and the remaining weights are renormalised. "No evidence" is never treated
   as 0.
4. Coverage is the share of configured weight that has evidence (0-100). It is reported
   alongside the overall so a high overall with low coverage is visible.
5. Level = the threshold with the highest min_score <= the (rounded) overall; none -> null.
6. Role score: weighted mean over the role's skills that have evidence, weighted by the
   role-skill weight; the rule's category weights are not used for role scores.
7. Values are rounded half-up to 2 decimal places.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from math import fsum

STATUS_READY = "READY"
STATUS_GAP = "GAP"
STATUS_NO_EVIDENCE = "NO_EVIDENCE"
PRIORITY_NONE = "NONE"
PRIORITY_LOW = "LOW"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_HIGH = "HIGH"
PRIORITY_UNASSESSED = "UNASSESSED"


@dataclass(frozen=True)
class LevelThreshold:
    """A readiness level that starts at ``min_score``."""

    level: str
    min_score: float


@dataclass(frozen=True)
class RuleConfig:
    """The institutional rule inputs the engine needs (all supplied by an admin-made rule)."""

    rule_id: int
    version: int
    weights: Mapping[int, float]
    level_thresholds: Sequence[LevelThreshold]
    high_min_gap: float
    medium_min_gap: float


@dataclass(frozen=True)
class SkillEvidence:
    """A student's current score for one skill (evidence exists)."""

    skill_id: int
    skill_name: str
    category_id: int
    category_name: str
    score: float
    evidence_count: int
    last_result_id: int | None


@dataclass(frozen=True)
class RoleRequirement:
    """One skill requirement of a career role."""

    skill_id: int
    skill_name: str
    category_id: int
    category_name: str
    required_level: float
    weight: float


@dataclass(frozen=True)
class CategoryScore:
    """Score of a category (``score`` is None when it has no evidence)."""

    category_id: int
    category_name: str
    weight: float
    score: float | None
    evidence_count: int


@dataclass(frozen=True)
class GapItem:
    """Gap analysis of one role skill."""

    skill_id: int
    skill_name: str
    current: float | None
    required: float
    gap: float | None
    status: str
    priority: str
    recommended_action: str


@dataclass(frozen=True)
class Computation:
    """Engine output."""

    overall: float | None
    level: str | None
    coverage: float
    category_scores: list[CategoryScore] = field(default_factory=list)
    evidence: list[SkillEvidence] = field(default_factory=list)
    gaps: list[GapItem] = field(default_factory=list)


def round2(value: float) -> float:
    """Round half-up to 2 decimal places (deterministic, unlike binary float rounding)."""
    return float(Decimal(repr(float(value))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def resolve_level(overall: float | None, thresholds: Sequence[LevelThreshold]) -> str | None:
    """Level with the highest min_score <= overall; None when overall is None or no match."""
    if overall is None:
        return None
    for threshold in sorted(thresholds, key=lambda t: (-t.min_score, t.level)):
        if threshold.min_score <= overall:
            return threshold.level
    return None


def _mean(values: Sequence[float]) -> float:
    return fsum(values) / len(values)


def compute_general(
    rule: RuleConfig,
    skills: Sequence[SkillEvidence],
    category_names: Mapping[int, str],
) -> Computation:
    """General (role-less) readiness: weighted mean of category means over the rule weights."""
    by_category: dict[int, list[SkillEvidence]] = defaultdict(list)
    for item in skills:
        if item.category_id in rule.weights:
            by_category[item.category_id].append(item)

    categories: list[CategoryScore] = []
    evidence: list[SkillEvidence] = []
    weighted_sum = 0.0
    evidenced_weight = 0.0
    total_weight = fsum(rule.weights.values())
    for category_id in sorted(rule.weights, key=lambda c: (category_names.get(c, ""), c)):
        weight = float(rule.weights[category_id])
        items = sorted(by_category.get(category_id, []), key=lambda s: (s.skill_name, s.skill_id))
        score = round2(_mean([s.score for s in items])) if items else None
        if items:
            weighted_sum += weight * _mean([s.score for s in items])
            evidenced_weight += weight
            evidence.extend(items)
        categories.append(
            CategoryScore(
                category_id=category_id,
                category_name=category_names.get(category_id, f"Category {category_id}"),
                weight=weight,
                score=score,
                evidence_count=sum(s.evidence_count for s in items),
            )
        )
    if evidenced_weight <= 0 or total_weight <= 0:
        return Computation(None, None, 0.0, categories, evidence, [])
    overall = round2(weighted_sum / evidenced_weight)
    return Computation(
        overall=overall,
        level=resolve_level(overall, rule.level_thresholds),
        coverage=round2(evidenced_weight / total_weight * 100),
        category_scores=categories,
        evidence=evidence,
        gaps=[],
    )


def _gap_item(rule: RuleConfig, req: RoleRequirement, current: float | None) -> GapItem:
    required = round2(req.required_level)
    if current is None:
        return GapItem(
            skill_id=req.skill_id,
            skill_name=req.skill_name,
            current=None,
            required=required,
            gap=None,
            status=STATUS_NO_EVIDENCE,
            priority=PRIORITY_UNASSESSED,
            recommended_action=f"Complete an assessment that covers {req.skill_name}",
        )
    current = round2(current)
    gap = round2(max(required - current, 0.0))
    if gap == 0:
        return GapItem(
            skill_id=req.skill_id,
            skill_name=req.skill_name,
            current=current,
            required=required,
            gap=0.0,
            status=STATUS_READY,
            priority=PRIORITY_NONE,
            recommended_action="No action needed",
        )
    if gap >= rule.high_min_gap:
        priority = PRIORITY_HIGH
    elif gap >= rule.medium_min_gap:
        priority = PRIORITY_MEDIUM
    else:
        priority = PRIORITY_LOW
    return GapItem(
        skill_id=req.skill_id,
        skill_name=req.skill_name,
        current=current,
        required=required,
        gap=gap,
        status=STATUS_GAP,
        priority=priority,
        recommended_action=(
            f"Improve {req.skill_name}: close a gap of {gap:g} points "
            f"(current {current:g}, required {required:g})"
        ),
    )


def compute_role(
    rule: RuleConfig,
    requirements: Sequence[RoleRequirement],
    skills: Sequence[SkillEvidence],
) -> Computation:
    """Role readiness: weighted mean over evidenced role skills, plus per-skill gaps."""
    evidence_by_skill = {s.skill_id: s for s in skills}
    reqs = sorted(requirements, key=lambda r: (r.skill_name, r.skill_id))
    total_weight = fsum(r.weight for r in reqs)
    weighted_sum = 0.0
    evidenced_weight = 0.0
    evidence: list[SkillEvidence] = []
    gaps: list[GapItem] = []
    grouped: dict[int, list[tuple[RoleRequirement, SkillEvidence | None]]] = defaultdict(list)
    for req in reqs:
        ev = evidence_by_skill.get(req.skill_id)
        grouped[req.category_id].append((req, ev))
        gaps.append(_gap_item(rule, req, ev.score if ev is not None else None))
        if ev is not None:
            weighted_sum += req.weight * ev.score
            evidenced_weight += req.weight
            evidence.append(ev)

    categories: list[CategoryScore] = []
    for category_id, pairs in sorted(
        grouped.items(), key=lambda kv: (kv[1][0][0].category_name, kv[0])
    ):
        scored = [ev for _, ev in pairs if ev is not None]
        categories.append(
            CategoryScore(
                category_id=category_id,
                category_name=pairs[0][0].category_name,
                weight=round2(fsum(r.weight for r, _ in pairs)),
                score=round2(_mean([e.score for e in scored])) if scored else None,
                evidence_count=sum(e.evidence_count for e in scored),
            )
        )
    if evidenced_weight <= 0 or total_weight <= 0:
        return Computation(None, None, 0.0, categories, evidence, gaps)
    overall = round2(weighted_sum / evidenced_weight)
    return Computation(
        overall=overall,
        level=resolve_level(overall, rule.level_thresholds),
        coverage=round2(evidenced_weight / total_weight * 100),
        category_scores=categories,
        evidence=evidence,
        gaps=gaps,
    )
