import type { InputHTMLAttributes } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  id: string;
  label: string;
}

export function FormField({ id, label, ...inputProps }: FormFieldProps) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} name={id} {...inputProps} />
    </div>
  );
}

interface FormMessageProps {
  message: string | null;
  tone?: 'error' | 'success';
}

export function FormMessage({ message, tone = 'error' }: FormMessageProps) {
  if (!message) return null;
  const color = tone === 'error' ? 'border-destructive/40 bg-destructive/10 text-destructive' : 'border-green-300 bg-green-50 text-green-800';
  return (
    <div role={tone === 'error' ? 'alert' : 'status'} className={`rounded-md border px-3 py-2 text-sm ${color}`}>
      {message}
    </div>
  );
}
