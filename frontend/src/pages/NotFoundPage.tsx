import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-2">
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <Link to="/" className="text-primary hover:underline">
        Go home
      </Link>
    </div>
  );
}
