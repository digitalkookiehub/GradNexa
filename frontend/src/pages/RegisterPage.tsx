import { Link, useNavigate } from 'react-router-dom';
import { RegisterForm } from '@/components/auth/RegisterForm';
import { AuthLayout } from '@/components/layout/AuthLayout';

export function RegisterPage() {
  const navigate = useNavigate();
  return (
    <AuthLayout
      title="Create your account"
      description="Join your college on GradNexa."
      footer={
        <>
          Already registered?{' '}
          <Link to="/login" className="text-primary hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <RegisterForm onSuccess={() => navigate('/login', { replace: true, state: { registered: true } })} />
    </AuthLayout>
  );
}
