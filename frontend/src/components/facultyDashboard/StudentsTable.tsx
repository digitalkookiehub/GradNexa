import { useMemo, useState } from 'react';
import { formatDate } from '@/lib/assessment';
import { formatDash } from '@/lib/dashboard';
import type { FacultyStudentRow } from '@/types';

type SortKey = 'name' | 'overall' | 'needs_support';
type SortDir = 'asc' | 'desc';

function compare(a: FacultyStudentRow, b: FacultyStudentRow, key: SortKey, dir: SortDir): number {
  const sign = dir === 'asc' ? 1 : -1;
  if (key === 'name') return sign * a.name.localeCompare(b.name);
  if (key === 'overall') {
    // Not-scored students always sort last regardless of direction.
    if (a.overall === null && b.overall === null) return a.name.localeCompare(b.name);
    if (a.overall === null) return 1;
    if (b.overall === null) return -1;
    return sign * (a.overall - b.overall) || a.name.localeCompare(b.name);
  }
  return sign * (Number(a.needs_support) - Number(b.needs_support)) || a.name.localeCompare(b.name);
}

interface SortHeaderProps {
  label: string;
  sortKey: SortKey;
  active: SortKey;
  dir: SortDir;
  onSort: (key: SortKey) => void;
}

function SortHeader({ label, sortKey, active, dir, onSort }: SortHeaderProps) {
  const isActive = active === sortKey;
  const ariaSort = isActive ? (dir === 'asc' ? 'ascending' : 'descending') : 'none';
  return (
    <th scope="col" aria-sort={ariaSort} className="py-2 pr-4 font-medium">
      <button type="button" className="font-medium hover:text-foreground" onClick={() => onSort(sortKey)}>
        {label}
        {isActive ? (dir === 'asc' ? ' (ascending)' : ' (descending)') : ''}
      </button>
    </th>
  );
}

interface StudentsTableProps {
  students: FacultyStudentRow[];
}

export function StudentsTable({ students }: StudentsTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [dir, setDir] = useState<SortDir>('asc');

  const sorted = useMemo(() => [...students].sort((a, b) => compare(a, b, sortKey, dir)), [students, sortKey, dir]);

  const onSort = (key: SortKey): void => {
    if (key === sortKey) {
      setDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setDir(key === 'needs_support' ? 'desc' : 'asc');
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Assigned students</caption>
        <thead>
          <tr className="border-b text-muted-foreground">
            <SortHeader label="Student" sortKey="name" active={sortKey} dir={dir} onSort={onSort} />
            <SortHeader label="Overall" sortKey="overall" active={sortKey} dir={dir} onSort={onSort} />
            <th scope="col" className="py-2 pr-4 font-medium">Level</th>
            <th scope="col" className="py-2 pr-4 font-medium">Coverage (%)</th>
            <th scope="col" className="py-2 pr-4 font-medium">High-priority gaps</th>
            <th scope="col" className="py-2 pr-4 font-medium">Last assessment</th>
            <SortHeader label="Needs support" sortKey="needs_support" active={sortKey} dir={dir} onSort={onSort} />
          </tr>
        </thead>
        <tbody>
          {sorted.map((s) => (
            <tr key={s.student_id} className="border-b align-top last:border-0">
              <th scope="row" className="py-2 pr-4 text-left font-normal">
                <div className="font-medium">{s.name}</div>
                <div className="text-xs text-muted-foreground">
                  {s.email}
                  {s.roll_number ? ` · ${s.roll_number}` : ''}
                  {s.department_name ? ` · ${s.department_name}` : ''}
                </div>
              </th>
              <td className="py-2 pr-4 tabular-nums">{formatDash(s.overall)}</td>
              <td className="py-2 pr-4">{s.level ?? 'Not scored'}</td>
              <td className="py-2 pr-4 tabular-nums">{formatDash(s.coverage)}</td>
              <td className="py-2 pr-4 tabular-nums">{s.high_priority_gap_count}</td>
              <td className="py-2 pr-4">
                {s.last_assessment_percentage === null ? (
                  '-'
                ) : (
                  <>
                    <span className="tabular-nums">{formatDash(s.last_assessment_percentage)}%</span>
                    {s.last_assessment_at && <div className="text-xs text-muted-foreground">{formatDate(s.last_assessment_at)}</div>}
                  </>
                )}
              </td>
              <td className="py-2 pr-4">
                {s.needs_support ? (
                  <div className="space-y-1">
                    <span className="font-medium">Yes</span>
                    <ul className="flex flex-wrap gap-1" aria-label={`Reasons for ${s.name}`}>
                      {s.support_reasons.map((r) => (
                        <li key={r} className="rounded-full border bg-muted px-2 py-0.5 text-xs">
                          {r}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  'No'
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
