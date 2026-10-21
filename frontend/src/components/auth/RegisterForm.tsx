import { useState, type FormEvent } from 'react';
import { FormField, FormMessage } from './FormField';
import { Button } from '@/components/ui/button';
import { authService } from '@/services/authService';
import { getErrorMessage } from '@/lib/errors';

interface RegisterFormProps {
  onSuccess?: () => void;
}

export function RegisterForm({ onSuccess }: RegisterFormProps) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [collegeCode, setCollegeCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    setSubmitting(true);
    try {
      await authService.register({
        full_name: fullName.trim(),
        email,
        password,
        college_code: collegeCode.trim(),
      });
      onSuccess?.();
    } catch (err) {
      setError(getErrorMessage(err, 'Registration failed.'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <FormMessage message={error} />
      <FormField id="full_name" label="Full name" autoComplete="name" required value={fullName} onChange={(e) => setFullName(e.target.value)} disabled={submitting} />
      <FormField id="email" label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} disabled={submitting} />
      <FormField id="password" label="Password" type="password" autoComplete="new-password" required value={password} onChange={(e) => setPassword(e.target.value)} disabled={submitting} />
      <FormField id="college_code" label="College code" required value={collegeCode} onChange={(e) => setCollegeCode(e.target.value)} disabled={submitting} />
      <Button type="submit" className="w-full" disabled={submitting || !fullName || !email || !password || !collegeCode}>
        {submitting ? 'Creating account...' : 'Create account'}
      </Button>
    </form>
  );
}
