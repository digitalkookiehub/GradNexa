import { SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { KIND_CLASSES, KIND_LABELS, STATUS_LABELS, STATUS_ORDER } from '@/lib/roadmap';
import type { PlanItem, PlanItemStatus } from '@/types';

interface PlanItemRowProps {
  item: PlanItem;
  pending: boolean;
  onStatusChange: (item: PlanItem, status: PlanItemStatus) => void;
}

export function PlanItemRow({ item, pending, onStatusChange }: PlanItemRowProps) {
  const done = item.status === 'DONE';
  return (
    <li className="space-y-2 rounded-md border p-3" data-testid={`plan-item-${item.id}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${KIND_CLASSES[item.kind]}`}>{KIND_LABELS[item.kind]}</span>
        {item.skill_name && <span className="text-xs text-muted-foreground">{item.skill_name}</span>}
      </div>
      <p className={done ? 'text-sm text-muted-foreground line-through' : 'text-sm'}>{item.task}</p>
      {item.resource ? (
        <a href={item.resource.url} target="_blank" rel="noopener noreferrer" className="text-sm text-primary hover:underline">
          {item.resource.title}
        </a>
      ) : (
        item.kind === 'LEARN' && <p className="text-xs text-muted-foreground">No approved learning resource is configured for this task.</p>
      )}
      <div className="flex items-center gap-2">
        <label htmlFor={`status-${item.id}`} className="text-xs text-muted-foreground">
          Status
        </label>
        <select
          id={`status-${item.id}`}
          className={`${SELECT_CLASS} max-w-[11rem]`}
          value={item.status}
          disabled={pending}
          aria-label={`Status for ${item.task}`}
          onChange={(e) => onStatusChange(item, e.target.value as PlanItemStatus)}
        >
          {STATUS_ORDER.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABELS[s]}
            </option>
          ))}
        </select>
      </div>
    </li>
  );
}
