import { AcademicRecordsPanel } from '@/components/student/AcademicRecordsPanel';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function AcademicsPage() {
  return (
    <Card className="mx-auto max-w-2xl">
      <CardHeader>
        <CardTitle>Academics</CardTitle>
        <CardDescription>Semester-wise CGPA, arrears and attendance.</CardDescription>
      </CardHeader>
      <CardContent>
        <AcademicRecordsPanel />
      </CardContent>
    </Card>
  );
}
