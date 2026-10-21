import { ProfileForm } from '@/components/auth/ProfileForm';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function ProfilePage() {
  return (
    <Card className="mx-auto max-w-xl">
      <CardHeader>
        <CardTitle>Your profile</CardTitle>
        <CardDescription>View and update your account details.</CardDescription>
      </CardHeader>
      <CardContent>
        <ProfileForm />
      </CardContent>
    </Card>
  );
}
