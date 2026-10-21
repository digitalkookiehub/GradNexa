import type { UserRole } from '@/types';

/** Default page after login / at "/" for each role. */
export function landingPathFor(role: UserRole | undefined): string {
  if (role === 'STUDENT') return '/dashboard';
  if (role === 'TPO') return '/placement';
  if (role === 'FACULTY') return '/faculty';
  if (role === 'HOD') return '/hod';
  return '/profile';
}
