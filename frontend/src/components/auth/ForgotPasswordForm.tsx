import { useState, type FormEvent } from 'react';
import { FormField, FormMessage } from './FormField';
import { Button } from '@/components/ui/button';
import { authService } from '@/services/authService';
import { getErrorMessage } from '@/lib/errors';

export function ForgotPasswordForm() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await authService.forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (sent) {
    return <FormMessage tone="success" message="If an account exists for that email, a reset link has been sent." />;
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <FormMessage message={error} />
      <FormField id="email" label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} disabled={submitting} />
      <Button type="submit" className="w-full" disabled={submitting || !email}>
        {submitting ? 'Sending...' : 'Send reset link'}
      </Button>
    </form>
  );
}
