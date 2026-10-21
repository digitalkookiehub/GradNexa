import type { ReactNode } from 'react';
import { Brand } from './Brand';
import { PageWrapper } from './PageWrapper';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface AuthLayoutProps {
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function AuthLayout({ title, description, children, footer }: AuthLayoutProps) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-br from-indigo-50 via-white to-sky-50 px-4 py-10">
      <div className="pointer-events-none absolute -left-24 -top-24 h-80 w-80 rounded-full bg-indigo-200 opacity-40 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 -right-24 h-80 w-80 rounded-full bg-sky-200 opacity-40 blur-3xl" />
      <PageWrapper className="relative w-full max-w-md space-y-6">
        <Brand showTagline />
        <Card>
          <CardHeader>
            <CardTitle>{title}</CardTitle>
            {description && <CardDescription>{description}</CardDescription>}
          </CardHeader>
          <CardContent className="space-y-4">{children}</CardContent>
        </Card>
        {footer && <div className="text-center text-sm text-muted-foreground">{footer}</div>}
      </PageWrapper>
    </div>
  );
}
