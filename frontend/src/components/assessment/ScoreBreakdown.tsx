import { formatPercent } from '@/lib/assessment';
import type { SkillScore } from '@/types';

interface ScoreBreakdownProps {
  scores: SkillScore[];
}

export function ScoreBreakdown({ scores }: ScoreBreakdownProps) {
  if (scores.length === 0) return <p className="text-sm text-muted-foreground">No per-skill breakdown available.</p>;
  return (
    <ul className="space-y-3">
      {scores.map((s) => (
        <li key={s.skill_id} className="space-y-1">
          <div className="flex justify-between text-sm">
            <span className="font-medium">{s.skill_name}</span>
            <span>
              {s.score} / {s.max} ({formatPercent(s.percentage)})
            </span>
          </div>
          <progress
            className="h-2 w-full overflow-hidden rounded bg-muted [&::-moz-progress-bar]:bg-primary [&::-webkit-progress-bar]:bg-muted [&::-webkit-progress-value]:bg-primary"
            max={100}
            value={Math.min(100, Math.max(0, s.percentage))}
            aria-label={`${s.skill_name} score`}
          />
        </li>
      ))}
    </ul>
  );
}
