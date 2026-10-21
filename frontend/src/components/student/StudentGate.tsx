import { useEffect, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';
import { getErrorMessage } from '@/lib/errors';
import { studentService } from '@/services/studentService';

type GateState = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; complete: boolean };

/**
 * Wraps authenticated pages. Students with an incomplete profile are sent to
 * /onboarding; every other role passes straight through.
 */
export function StudentGate() {
  const { user } = useAuth();
  const isStudent = user?.role === 'STUDENT';
  const [state, setState] = useState<GateState>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!isStudent) return;
    let cancelled = false;
    studentService
      .getProfile()
      .then((p) => {
        if (!cancelled) setState({ status: 'ready', complete: p.profile_complete });
      })
      .catch((err: unknown) => {
        if (!cancelled) setState({ status: 'error', message: getErrorMessage(err, 'Could not load your student profile.') });
      });
    return () => {
      cancelled = true;
    };
  }, [isStudent, attempt]);

  if (!isStudent) return <Outlet />;

  if (state.status === 'loading') {
    return (
      <p role="status" className="py-12 text-center text-muted-foreground">
        Loading your profile...
      </p>
    );
  }
  if (state.status === 'error') {
    return (
      <div className="mx-auto max-w-md space-y-4 py-12">
        <FormMessage message={state.message} />
        <Button
          variant="outline"
          onClick={() => {
            setState({ status: 'loading' });
            setAttempt((a) => a + 1);
          }}
        >
          Retry
        </Button>
      </div>
    );
  }
  if (!state.complete) return <Navigate to="/onboarding" replace />;
  return <Outlet />;
}
