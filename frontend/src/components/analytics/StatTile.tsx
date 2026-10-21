interface StatTileProps {
  label: string;
  value: number;
}

export function StatTile({ label, value }: StatTileProps) {
  return (
    <div className="rounded-lg border bg-background p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="text-2xl font-bold tabular-nums">{value}</p>
    </div>
  );
}
