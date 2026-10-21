import { Label } from '@/components/ui/label';
import { SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import type { CareerRole } from '@/types';

interface RoleSelectProps {
  id: string;
  roles: CareerRole[];
  value: string;
  onChange: (value: string) => void;
  /** Adds a "General (no role)" option with the empty value. */
  allowGeneral: boolean;
  disabled?: boolean;
}

export function RoleSelect({ id, roles, value, onChange, allowGeneral, disabled = false }: RoleSelectProps) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>Career role</Label>
      <select id={id} className={SELECT_CLASS} value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled}>
        {allowGeneral ? <option value="">General (no role)</option> : <option value="">Select a role</option>}
        {roles.map((r) => (
          <option key={r.id} value={r.id}>
            {r.name}
          </option>
        ))}
      </select>
    </div>
  );
}
