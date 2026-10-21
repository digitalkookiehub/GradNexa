import type { HodHeatmapCell } from '@/types';

interface Step {
  min: number;
  className: string;
  label: string;
}

/** Fixed set of background steps. The number is always printed in the cell. */
const HEATMAP_STEPS: Step[] = [
  { min: 80, className: 'bg-blue-300 text-slate-900', label: '80 to 100' },
  { min: 60, className: 'bg-blue-200 text-slate-900', label: '60 to 79' },
  { min: 40, className: 'bg-blue-100 text-slate-900', label: '40 to 59' },
  { min: 20, className: 'bg-slate-100 text-slate-900', label: '20 to 39' },
  { min: 0, className: 'bg-slate-50 text-slate-900', label: '0 to 19' },
];

function heatmapClass(score: number | null): string {
  if (score === null) return 'text-muted-foreground';
  const step = HEATMAP_STEPS.find((s) => score >= s.min) ?? HEATMAP_STEPS[HEATMAP_STEPS.length - 1];
  return step.className;
}

interface SkillHeatmapProps {
  cells: HodHeatmapCell[];
}

export function SkillHeatmap({ cells }: SkillHeatmapProps) {
  const sorted = [...cells].sort((a, b) => a.category_name.localeCompare(b.category_name) || a.skill_name.localeCompare(b.skill_name));
  return (
    <div className="space-y-3">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Average skill score by skill</caption>
          <thead>
            <tr className="border-b text-muted-foreground">
              <th scope="col" className="py-2 pr-4 font-medium">Category</th>
              <th scope="col" className="py-2 pr-4 font-medium">Skill</th>
              <th scope="col" className="py-2 pr-4 font-medium">Students assessed</th>
              <th scope="col" className="py-2 font-medium">Average score</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((c) => (
              <tr key={c.skill_id} className="border-b last:border-0">
                <td className="py-2 pr-4">{c.category_name || '-'}</td>
                <th scope="row" className="py-2 pr-4 font-normal">{c.skill_name}</th>
                <td className="py-2 pr-4 tabular-nums">{c.students_assessed}</td>
                <td
                  className={`py-2 px-2 font-medium tabular-nums ${heatmapClass(c.average_score)}`}
                  data-testid={`heat-${c.skill_id}`}
                >
                  {c.average_score === null ? '-' : Math.round(c.average_score * 10) / 10}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span>Shading steps (score is always printed in the cell):</span>
        {[...HEATMAP_STEPS].reverse().map((s) => (
          <span key={s.min} className={`rounded border px-2 py-0.5 ${s.className}`}>
            {s.label}
          </span>
        ))}
      </p>
    </div>
  );
}
