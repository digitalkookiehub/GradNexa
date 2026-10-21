import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { FormField, FormMessage } from './FormField';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';
import { getErrorMessage } from '@/lib/errors';

interface LoginFormProps {
  onSuccess?: () => void;
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login({ email, password });
      onSuccess?.();
    } catch (err) {
      setError(getErrorMessage(err, 'Login failed. Check your credentials.'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <FormMessage message={error} />
      <FormField id="email" label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} disabled={submitting} />
      <FormField id="password" label="Password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} disabled={submitting} />
      <div className="text-right text-sm">
        <Link to="/forgot-password" className="text-primary hover:underline">
          Forgot password?
        </Link>
      </div>
      <Button type="submit" className="w-full" disabled={submitting || !email || !password}>
        {submitting ? 'Signing in...' : 'Sign in'}
      </Button>
    </form>
  );
}
