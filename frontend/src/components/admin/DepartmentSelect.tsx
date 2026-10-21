import { Label } from '@/components/ui/label';
import type { Department } from '@/types';

export const SELECT_CLASS =
  'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50';

interface DepartmentSelectProps {
  id: string;
  label: string;
  departments: Department[];
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  disabled?: boolean;
  invalid?: boolean;
}

export function DepartmentSelect({ id, label, departments, value, onChange, placeholder, disabled = false, invalid = false }: DepartmentSelectProps) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <select id={id} className={SELECT_CLASS} value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled} aria-invalid={invalid}>
        <option value="">{placeholder}</option>
        {departments.map((d) => (
          <option key={d.id} value={d.id}>
            {d.name}
          </option>
        ))}
      </select>
    </div>
  );
}
