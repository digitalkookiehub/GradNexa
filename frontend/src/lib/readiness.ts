import type { SkillCategory } from '@/types/assessment';
import type { Gap, GapPriority, GapStatus, LevelThreshold, ReadinessRuleInput } from '@/types/readiness';

export const PRIORITY_RANK: Record<GapPriority, number> = { HIGH: 0, MEDIUM: 1, LOW: 2, NONE: 3, UNASSESSED: 4 };

export const PRIORITY_LABELS: Record<GapPriority, string> = {
  HIGH: 'High',
  MEDIUM: 'Medium',
  LOW: 'Low',
  NONE: 'None',
  UNASSESSED: 'Unassessed',
};

export const PRIORITY_CLASSES: Record<GapPriority, string> = {
  HIGH: 'bg-red-100 text-red-800',
  MEDIUM: 'bg-amber-100 text-amber-800',
  LOW: 'bg-yellow-50 text-yellow-800',
  NONE: 'bg-green-100 text-green-800',
  UNASSESSED: 'bg-muted text-muted-foreground',
};

export const GAP_STATUS_LABELS: Record<GapStatus, string> = {
  READY: 'Ready',
  GAP: 'Gap',
  NO_EVIDENCE: 'No evidence',
};

/** HIGH first, then MEDIUM, LOW; NONE (ready) and UNASSESSED last. Larger gaps first within a priority. */
export function sortGaps(gaps: Gap[]): Gap[] {
  return [...gaps].sort((a, b) => {
    const byPriority = PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority];
    if (byPriority !== 0) return byPriority;
    const byGap = (b.gap ?? 0) - (a.gap ?? 0);
    if (byGap !== 0) return byGap;
    return a.skill_name.localeCompare(b.skill_name);
  });
}

export function formatScore(value: number | null): string {
  return value === null ? '-' : String(Math.round(value * 10) / 10);
}

export interface RuleFormValues {
  weights: Record<string, string>;
  levels: { level: string; min_score: string }[];
  highGap: string;
  mediumGap: string;
}

export interface RuleFormErrors {
  weights?: string;
  levels?: string;
  gaps?: string;
}

export type RuleValidation = { ok: true; payload: ReadinessRuleInput } | { ok: false; errors: RuleFormErrors };

function parseNumber(raw: string): number | null {
  if (raw.trim() === '') return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

/** Client-side mirror of the backend rule validation. The server remains the authority. */
export function validateRule(values: RuleFormValues, categories: SkillCategory[]): RuleValidation {
  const errors: RuleFormErrors = {};

  const weights: Record<string, number> = {};
  let weightProblem = false;
  for (const c of categories) {
    const raw = values.weights[String(c.id)] ?? '';
    if (raw.trim() === '') continue;
    const n = parseNumber(raw);
    if (n === null || n < 0) weightProblem = true;
    else weights[String(c.id)] = n;
  }
  const total = Object.values(weights).reduce((a, b) => a + b, 0);
  if (weightProblem) errors.weights = 'Weights must be numbers that are zero or greater.';
  else if (total <= 0) errors.weights = 'At least one category needs a weight greater than zero.';

  const levels: LevelThreshold[] = [];
  const seenNames = new Set<string>();
  const seenScores = new Set<number>();
  if (values.levels.length === 0) errors.levels = 'Add at least one level.';
  for (const row of values.levels) {
    const name = row.level.trim();
    const score = parseNumber(row.min_score);
    if (!name) {
      errors.levels = 'Every level needs a name.';
      break;
    }
    if (score === null || score < 0 || score > 100) {
      errors.levels = 'Level minimum scores must be numbers between 0 and 100.';
      break;
    }
    if (seenNames.has(name.toLowerCase())) {
      errors.levels = `Duplicate level name: ${name}.`;
      break;
    }
    if (seenScores.has(score)) {
      errors.levels = `Two levels share the minimum score ${score}.`;
      break;
    }
    seenNames.add(name.toLowerCase());
    seenScores.add(score);
    levels.push({ level: name, min_score: score });
  }
  if (!errors.levels && !levels.some((l) => l.min_score === 0)) {
    errors.levels = 'One level must have a minimum score of 0 so every score gets a level.';
  }

  const high = parseNumber(values.highGap);
  const medium = parseNumber(values.mediumGap);
  if (high === null || medium === null || high < 0 || medium < 0) {
    errors.gaps = 'Gap thresholds must be numbers that are zero or greater.';
  } else if (high < medium) {
    errors.gaps = 'The high-priority gap must be greater than or equal to the medium-priority gap.';
  }

  if (errors.weights || errors.levels || errors.gaps || high === null || medium === null) return { ok: false, errors };
  return {
    ok: true,
    payload: {
      weights,
      level_thresholds: [...levels].sort((a, b) => b.min_score - a.min_score),
      gap_thresholds: { high_min_gap: high, medium_min_gap: medium },
    },
  };
}
