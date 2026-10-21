import { Navigate, Route, Routes } from 'react-router-dom';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { StudentGate } from '@/components/student/StudentGate';
import { AppLayout } from '@/components/layout/AppLayout';
import { useAuth } from '@/hooks/useAuth';
import { landingPathFor } from '@/lib/landing';
import { AdminAssessmentDetailPage } from '@/pages/AdminAssessmentDetailPage';
import { AdminAssessmentsPage } from '@/pages/AdminAssessmentsPage';
import { AdminCompaniesPage } from '@/pages/AdminCompaniesPage';
import { AdminJobDetailPage } from '@/pages/AdminJobDetailPage';
import { AdminJobsPage } from '@/pages/AdminJobsPage';
import { AdminLearningResourcesPage } from '@/pages/AdminLearningResourcesPage';
import { AdminCareerRolesPage } from '@/pages/AdminCareerRolesPage';
import { AdminReadinessRulesPage } from '@/pages/AdminReadinessRulesPage';
import { AdminSkillsPage } from '@/pages/AdminSkillsPage';
import { AssessmentsPage } from '@/pages/AssessmentsPage';
import { AttemptPage } from '@/pages/AttemptPage';
import { CareerDetailPage } from '@/pages/CareerDetailPage';
import { CareersPage } from '@/pages/CareersPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { PlacementDashboardPage } from '@/pages/PlacementDashboardPage';
import { PlanPage } from '@/pages/PlanPage';
import { PlanProgressPage } from '@/pages/PlanProgressPage';
import { ResumeAnalysisPage } from '@/pages/ResumeAnalysisPage';
import { ResumePage } from '@/pages/ResumePage';
import { HistoryPage } from '@/pages/HistoryPage';
import { AdminInterviewQuestionsPage } from '@/pages/AdminInterviewQuestionsPage';
import { JobDetailPage } from '@/pages/JobDetailPage';
import { JobsPage } from '@/pages/JobsPage';
import { InterviewPage } from '@/pages/InterviewPage';
import { InterviewResultPage } from '@/pages/InterviewResultPage';
import { InterviewSessionPage } from '@/pages/InterviewSessionPage';
import { QuestionBankPage } from '@/pages/QuestionBankPage';
import { ReadinessPage } from '@/pages/ReadinessPage';
import { SkillGapsPage } from '@/pages/SkillGapsPage';
import { ResultPage } from '@/pages/ResultPage';
import { AcademicsPage } from '@/pages/AcademicsPage';
import { ForgotPasswordPage } from '@/pages/ForgotPasswordPage';
import { LoginPage } from '@/pages/LoginPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { OnboardingPage } from '@/pages/OnboardingPage';
import { ProfilePage } from '@/pages/ProfilePage';
import { ProjectsPage } from '@/pages/ProjectsPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { ResetPasswordPage } from '@/pages/ResetPasswordPage';
import { AdminHodAssignmentsPage } from '@/pages/AdminHodAssignmentsPage';
import { FacultyDashboardPage } from '@/pages/FacultyDashboardPage';
import { HodDashboardPage } from '@/pages/HodDashboardPage';
import { AdminMcpToolsPage } from '@/pages/AdminMcpToolsPage';
import { AdminUsersPage } from '@/pages/AdminUsersPage';
import { GuidePage } from '@/pages/GuidePage';
import { AssistantPage } from '@/pages/AssistantPage';
import { KnowledgeAdminPage } from '@/pages/KnowledgeAdminPage';
import { KnowledgeSearchPage } from '@/pages/KnowledgeSearchPage';

function LandingRedirect() {
  const { user, isAuthenticated, isLoading } = useAuth();
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center" role="status">
        Loading...
      </div>
    );
  }
  return <Navigate to={isAuthenticated ? landingPathFor(user?.role) : '/login'} replace />;
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route element={<StudentGate />}>
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/knowledge" element={<KnowledgeSearchPage />} />
          </Route>
        </Route>
      </Route>
      <Route element={<ProtectedRoute allowedRoles={['STUDENT']} />}>
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route element={<AppLayout />}>
          <Route element={<StudentGate />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/assistant" element={<AssistantPage />} />
            <Route path="/profile/academics" element={<AcademicsPage />} />
            <Route path="/profile/projects" element={<ProjectsPage />} />
            <Route path="/assessments" element={<AssessmentsPage />} />
            <Route path="/assessments/history" element={<HistoryPage />} />
            <Route path="/assessments/:id/attempt" element={<AttemptPage />} />
            <Route path="/attempts/:attemptId/result" element={<ResultPage />} />
            <Route path="/readiness" element={<ReadinessPage />} />
            <Route path="/readiness/gaps" element={<SkillGapsPage />} />
            <Route path="/careers" element={<CareersPage />} />
            <Route path="/careers/:id" element={<CareerDetailPage />} />
            <Route path="/plan" element={<PlanPage />} />
            <Route path="/plan/progress" element={<PlanProgressPage />} />
            <Route path="/interview" element={<InterviewPage />} />
            <Route path="/interview/:id" element={<InterviewSessionPage />} />
            <Route path="/interview/:id/result" element={<InterviewResultPage />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/jobs/:id" element={<JobDetailPage />} />
            <Route path="/resume" element={<ResumePage />} />
            <Route path="/resume/:id/analysis" element={<ResumeAnalysisPage />} />
          </Route>
        </Route>
      </Route>
      <Route element={<ProtectedRoute allowedRoles={['TPO', 'ADMIN']} />}>
        <Route element={<AppLayout />}>
          <Route path="/placement" element={<PlacementDashboardPage />} />
          <Route path="/admin/companies" element={<AdminCompaniesPage />} />
          <Route path="/admin/jobs" element={<AdminJobsPage />} />
          <Route path="/admin/jobs/:id" element={<AdminJobDetailPage />} />
        </Route>
      </Route>
      <Route element={<ProtectedRoute allowedRoles={['ADMIN', 'FACULTY']} />}>
        <Route element={<AppLayout />}>
          <Route path="/admin/assessments" element={<AdminAssessmentsPage />} />
          <Route path="/admin/assessments/:id" element={<AdminAssessmentDetailPage />} />
          <Route path="/admin/question-bank" element={<QuestionBankPage />} />
          <Route path="/admin/knowledge" element={<KnowledgeAdminPage />} />
          <Route path="/admin/learning-resources" element={<AdminLearningResourcesPage />} />
          <Route path="/admin/interview-questions" element={<AdminInterviewQuestionsPage />} />
        </Route>
      </Route>
      <Route element={<ProtectedRoute allowedRoles={['FACULTY']} />}>
        <Route element={<AppLayout />}>
          <Route path="/faculty" element={<FacultyDashboardPage />} />
        </Route>
      </Route>
      <Route element={<ProtectedRoute allowedRoles={['HOD']} />}>
        <Route element={<AppLayout />}>
          <Route path="/hod" element={<HodDashboardPage />} />
        </Route>
      </Route>
      <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
        <Route element={<AppLayout />}>
          <Route path="/admin/hod-assignments" element={<AdminHodAssignmentsPage />} />
          <Route path="/admin/skills" element={<AdminSkillsPage />} />
          <Route path="/admin/mcp-tools" element={<AdminMcpToolsPage />} />
          <Route path="/admin/users" element={<AdminUsersPage />} />
          <Route path="/guide" element={<GuidePage />} />
          <Route path="/admin/readiness-rules" element={<AdminReadinessRulesPage />} />
          <Route path="/admin/career-roles" element={<AdminCareerRolesPage />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
