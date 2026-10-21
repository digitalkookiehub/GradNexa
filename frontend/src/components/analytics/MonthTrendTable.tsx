import { formatDash } from '@/lib/dashboard';

export interface TrendRow {
  month: string;
  count: number;
  /** Average on a 0-100 scale, or null when there is no data. */
  average: number | null;
}

interface MonthTrendTableProps {
  caption: string;
  countLabel: string;
  averageLabel: string;
  rows: TrendRow[];
}

/** Trend as a table: month, count, average number plus a small native progress bar. */
export function MonthTrendTable({ caption, countLabel, averageLabel, rows }: MonthTrendTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="border-b text-muted-foreground">
            <th scope="col" className="py-2 pr-4 font-medium">Month</th>
            <th scope="col" className="py-2 pr-4 font-medium">{countLabel}</th>
            <th scope="col" className="py-2 pr-4 font-medium">{averageLabel}</th>
            <th scope="col" className="py-2 font-medium"><span className="sr-only">Average bar</span></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.month} className="border-b last:border-0">
              <th scope="row" className="py-2 pr-4 font-normal">{r.month}</th>
              <td className="py-2 pr-4 tabular-nums">{r.count}</td>
              <td className="py-2 pr-4 tabular-nums">{formatDash(r.average)}</td>
              <td className="w-32 py-2">
                {r.average !== null && (
                  <progress
                    className="h-2 w-full overflow-hidden rounded [&::-moz-progress-bar]:bg-primary [&::-webkit-progress-bar]:bg-muted [&::-webkit-progress-value]:bg-primary"
                    value={Math.max(0, Math.min(r.average, 100))}
                    max={100}
                    aria-label={`${r.month} ${averageLabel}: ${formatDash(r.average)}`}
                  />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
