import { Button } from '@/components/ui/button';

interface ConfirmPanelProps {
  title: string;
  message: string;
  confirmLabel: string;
  busy?: boolean;
  destructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** In-page confirmation (window.confirm is unavailable). */
export function ConfirmPanel({ title, message, confirmLabel, busy = false, destructive = false, onConfirm, onCancel }: ConfirmPanelProps) {
  return (
    <div role="alertdialog" aria-label={title} className="space-y-3 rounded-md border bg-background p-4">
      <h2 className="font-semibold">{title}</h2>
      <p className="text-sm text-muted-foreground">{message}</p>
      <div className="flex gap-2">
        <Button variant={destructive ? 'destructive' : 'default'} onClick={onConfirm} disabled={busy}>
          {busy ? 'Working...' : confirmLabel}
        </Button>
        <Button variant="outline" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
