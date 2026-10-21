import { CertificationsPanel } from '@/components/student/CertificationsPanel';
import { ProjectsPanel } from '@/components/student/ProjectsPanel';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function ProjectsPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Projects</CardTitle>
          <CardDescription>Showcase what you have built.</CardDescription>
        </CardHeader>
        <CardContent>
          <ProjectsPanel />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Certifications</CardTitle>
          <CardDescription>Courses and credentials you have earned.</CardDescription>
        </CardHeader>
        <CardContent>
          <CertificationsPanel />
        </CardContent>
      </Card>
    </div>
  );
}
