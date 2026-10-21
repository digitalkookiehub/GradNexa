import { Link } from 'react-router-dom';
import { ForgotPasswordForm } from '@/components/auth/ForgotPasswordForm';
import { AuthLayout } from '@/components/layout/AuthLayout';

export function ForgotPasswordPage() {
  return (
    <AuthLayout
      title="Forgot your password?"
      description="Enter your email and we will send you a reset link."
      footer={
        <Link to="/login" className="text-primary hover:underline">
          Back to sign in
        </Link>
      }
    >
      <ForgotPasswordForm />
    </AuthLayout>
  );
}
