import type { CareerGoal, CareerGoalInput, Plan, PlanItem, PlanItemKind, PlanItemStatus, PlanStatus } from '@/types';

export const KIND_LABELS: Record<PlanItemKind, string> = { LEARN: 'Learn', PRACTICE: 'Practice', ASSESS: 'Assess', REASSESS: 'Reassess' };

export const KIND_CLASSES: Record<PlanItemKind, string> = {
  LEARN: 'bg-blue-100 text-blue-800',
  PRACTICE: 'bg-purple-100 text-purple-800',
  ASSESS: 'bg-amber-100 text-amber-800',
  REASSESS: 'bg-green-100 text-green-800',
};

export const STATUS_LABELS: Record<PlanItemStatus, string> = { TODO: 'To do', IN_PROGRESS: 'In progress', DONE: 'Done' };
export const STATUS_ORDER: PlanItemStatus[] = ['TODO', 'IN_PROGRESS', 'DONE'];

export const PLAN_STATUS_LABELS: Record<PlanStatus, string> = { ACTIVE: 'Active', COMPLETED: 'Completed', ARCHIVED: 'Archived' };

export function renumber(goals: CareerGoal[]): CareerGoal[] {
  return goals.map((g, i) => ({ ...g, priority: i + 1 }));
}

export function toggleGoal(goals: CareerGoal[], roleId: number, roleName: string): CareerGoal[] {
  if (goals.some((g) => g.career_role_id === roleId)) {
    return renumber(goals.filter((g) => g.career_role_id !== roleId));
  }
  return renumber([...goals, { career_role_id: roleId, role_name: roleName, priority: goals.length + 1 }]);
}

export function moveGoal(goals: CareerGoal[], index: number, direction: -1 | 1): CareerGoal[] {
  const target = index + direction;
  if (index < 0 || index >= goals.length || target < 0 || target >= goals.length) return goals;
  const next = [...goals];
  [next[index], next[target]] = [next[target], next[index]];
  return renumber(next);
}

export function goalInputs(goals: CareerGoal[]): CareerGoalInput[] {
  return goals.map((g, i) => ({ career_role_id: g.career_role_id, priority: i + 1 }));
}

export function goalsKey(goals: CareerGoal[]): string {
  return goals.map((g) => g.career_role_id).join(',');
}

/** Returns an error message, or null when the URL is an acceptable http/https URL. */
export function validateResourceUrl(raw: string): string | null {
  const value = raw.trim();
  if (!value) return 'Enter a URL.';
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    return 'Enter a valid URL, including http:// or https://.';
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return 'The URL must start with http:// or https://.';
  if (!parsed.hostname) return 'Enter a valid URL, including http:// or https://.';
  return null;
}

export function formatDelta(value: number | null): string {
  if (value === null) return 'n/a';
  const rounded = Math.round(value * 10) / 10;
  return rounded > 0 ? `+${rounded}` : String(rounded);
}

/** Returns a copy of the plan with one item patched and the progress counters recomputed. */
export function replaceItem(plan: Plan, itemId: number, patch: Partial<PlanItem>): Plan {
  const weeks = plan.weeks.map((w) => ({ ...w, items: w.items.map((i) => (i.id === itemId ? { ...i, ...patch } : i)) }));
  const all = weeks.flatMap((w) => w.items);
  const done = all.filter((i) => i.status === 'DONE').length;
  const total = all.length;
  return { ...plan, weeks, progress: { done, total, percent: total === 0 ? 0 : Math.round((done / total) * 100) } };
}
