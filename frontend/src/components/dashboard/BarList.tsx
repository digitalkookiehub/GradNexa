export interface BarListItem {
  key: string;
  label: string;
  value: number;
  /** Text shown next to the bar, e.g. "72 / 100" or "5 students". */
  valueText: string;
  /** Optional secondary text next to the label. */
  hint?: string;
}

interface BarListProps {
  items: BarListItem[];
  max: number;
  ariaLabel: string;
}

/**
 * Accessible horizontal bars: every row has a visible label and number, and the
 * list itself is the text alternative to the native <progress> element.
 */
export function BarList({ items, max, ariaLabel }: BarListProps) {
  const safeMax = max > 0 ? max : 1;
  return (
    <ul className="space-y-3" aria-label={ariaLabel}>
      {items.map((item) => (
        <li key={item.key} className="space-y-1">
          <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
            <span className="font-medium">
              {item.label}
              {item.hint && <span className="ml-2 font-normal text-muted-foreground">{item.hint}</span>}
            </span>
            <span className="tabular-nums">{item.valueText}</span>
          </div>
          <progress
            className="h-2 w-full overflow-hidden rounded [&::-moz-progress-bar]:bg-primary [&::-webkit-progress-bar]:bg-muted [&::-webkit-progress-value]:bg-primary"
            value={Math.max(0, Math.min(item.value, safeMax))}
            max={safeMax}
            aria-label={`${item.label}: ${item.valueText}`}
          />
        </li>
      ))}
    </ul>
  );
}
