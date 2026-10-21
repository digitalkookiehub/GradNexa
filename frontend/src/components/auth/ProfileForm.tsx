import { useState, type FormEvent } from 'react';
import { FormField, FormMessage } from './FormField';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';
import { getErrorMessage } from '@/lib/errors';

export function ProfileForm() {
  const { user, updateProfile } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name ?? '');
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (!user) return null;

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError(null);
    setSaved(false);
    setSubmitting(true);
    try {
      await updateProfile(fullName.trim());
      setSaved(true);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not update profile.'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <FormMessage message={error} />
      <FormMessage tone="success" message={saved ? 'Profile updated.' : null} />
      <FormField id="email" label="Email" value={user.email} disabled readOnly />
      <FormField id="role" label="Role" value={user.role} disabled readOnly />
      <FormField id="full_name" label="Full name" required value={fullName} onChange={(e) => { setFullName(e.target.value); setSaved(false); }} disabled={submitting} />
      <Button type="submit" disabled={submitting || !fullName.trim() || fullName.trim() === user.full_name}>
        {submitting ? 'Saving...' : 'Save changes'}
      </Button>
    </form>
  );
}
