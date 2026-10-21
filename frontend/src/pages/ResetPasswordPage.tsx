import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ResetPasswordForm } from '@/components/auth/ResetPasswordForm';
import { FormMessage } from '@/components/auth/FormField';
import { AuthLayout } from '@/components/layout/AuthLayout';

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get('token');

  return (
    <AuthLayout
      title="Reset your password"
      description="Choose a new password."
      footer={
        <Link to="/login" className="text-primary hover:underline">
          Back to sign in
        </Link>
      }
    >
      {token ? (
        <ResetPasswordForm token={token} onSuccess={() => navigate('/login', { replace: true, state: { reset: true } })} />
      ) : (
        <FormMessage message="This reset link is invalid or missing a token. Request a new one." />
      )}
    </AuthLayout>
  );
}
