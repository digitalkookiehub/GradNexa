import { useState, type FormEvent } from 'react';
import { FormField, FormMessage } from './FormField';
import { Button } from '@/components/ui/button';
import { authService } from '@/services/authService';
import { getErrorMessage } from '@/lib/errors';

interface ResetPasswordFormProps {
  token: string;
  onSuccess?: () => void;
}

export function ResetPasswordForm({ token, onSuccess }: ResetPasswordFormProps) {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setSubmitting(true);
    try {
      await authService.resetPassword(token, password);
      onSuccess?.();
    } catch (err) {
      setError(getErrorMessage(err, 'Could not reset password. The link may have expired.'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <FormMessage message={error} />
      <FormField id="new_password" label="New password" type="password" autoComplete="new-password" required value={password} onChange={(e) => setPassword(e.target.value)} disabled={submitting} />
      <FormField id="confirm_password" label="Confirm password" type="password" autoComplete="new-password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} disabled={submitting} />
      <Button type="submit" className="w-full" disabled={submitting || !password || !confirm}>
        {submitting ? 'Resetting...' : 'Reset password'}
      </Button>
    </form>
  );
}
