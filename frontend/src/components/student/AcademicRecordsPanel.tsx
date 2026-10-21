import { useCallback, useEffect, useState } from 'react';
import { AcademicRecordForm } from './AcademicRecordForm';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { getErrorMessage } from '@/lib/errors';
import { studentService } from '@/services/studentService';
import type { AcademicRecord, AcademicRecordInput } from '@/types';

interface AcademicRecordsPanelProps {
  onRecordsChange?: (records: AcademicRecord[]) => void;
}

export function AcademicRecordsPanel({ onRecordsChange }: AcademicRecordsPanelProps) {
  const [records, setRecords] = useState<AcademicRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);

  const update = useCallback(
    (next: AcademicRecord[]): void => {
      const sorted = [...next].sort((a, b) => a.semester - b.semester);
      setRecords(sorted);
      onRecordsChange?.(sorted);
    },
    [onRecordsChange],
  );

  useEffect(() => {
    let cancelled = false;
    studentService
      .listAcademicRecords()
      .then((data) => {
        if (!cancelled) update(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setLoadError(getErrorMessage(err, 'Could not load academic records.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async (input: AcademicRecordInput): Promise<void> => {
    const created = await studentService.createAcademicRecord(input);
    update([...records, created]);
  };

  const handleUpdate = async (id: number, input: AcademicRecordInput): Promise<void> => {
    const saved = await studentService.updateAcademicRecord(id, input);
    update(records.map((r) => (r.id === id ? saved : r)));
    setEditingId(null);
  };

  return (
    <div className="space-y-6">
      <FormMessage message={loadError} />
      {loading ? (
        <p role="status" className="text-sm text-muted-foreground">
          Loading academic records...
        </p>
      ) : records.length === 0 ? (
        <p className="text-sm text-muted-foreground">No semester records yet.</p>
      ) : (
        <ul className="space-y-3" aria-label="Academic records">
          {records.map((r) =>
            editingId === r.id ? (
              <li key={r.id} className="rounded-md border p-4">
                <AcademicRecordForm initial={r} onSubmit={(input) => handleUpdate(r.id, input)} onCancel={() => setEditingId(null)} />
              </li>
            ) : (
              <li key={r.id} className="flex items-center justify-between rounded-md border p-4 text-sm">
                <div>
                  <div className="font-medium">Semester {r.semester}</div>
                  <div className="text-muted-foreground">
                    CGPA {r.cgpa.toFixed(2)} | Arrears {r.active_arrears}
                    {r.attendance_pct !== null && ` | Attendance ${r.attendance_pct}%`}
                  </div>
                </div>
                <Button type="button" variant="outline" size="sm" onClick={() => setEditingId(r.id)} aria-label={`Edit semester ${r.semester}`}>
                  Edit
                </Button>
              </li>
            ),
          )}
        </ul>
      )}
      <div className="rounded-md border p-4">
        <h3 className="mb-3 text-sm font-semibold">Add a semester</h3>
        <AcademicRecordForm onSubmit={handleCreate} />
      </div>
    </div>
  );
}
