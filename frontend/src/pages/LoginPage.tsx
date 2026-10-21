import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { LoginForm } from '@/components/auth/LoginForm';
import { FormMessage } from '@/components/auth/FormField';
import { AuthLayout } from '@/components/layout/AuthLayout';
import { landingPathFor } from '@/lib/landing';
import { useAuth } from '@/hooks/useAuth';

interface LoginLocationState {
  from?: string;
  registered?: boolean;
  reset?: boolean;
}

export function LoginPage() {
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state ?? {}) as LoginLocationState;

  if (isAuthenticated) return <Navigate to={state.from ?? landingPathFor(user?.role)} replace />;

  const notice = state.registered
    ? 'Account created. Please sign in.'
    : state.reset
      ? 'Password reset. Please sign in.'
      : null;

  return (
    <AuthLayout
      title="Welcome back"
      description="Sign in to your GradNexa account."
      footer={
        <>
          New here?{' '}
          <Link to="/register" className="text-primary hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <FormMessage tone="success" message={notice} />
      <LoginForm onSuccess={() => navigate(state.from ?? '/', { replace: true })} />
    </AuthLayout>
  );
}
