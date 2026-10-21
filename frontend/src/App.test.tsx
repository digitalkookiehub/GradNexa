import { render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from './App';
import { AuthStub, makeUser } from '@/test/helpers';
import type { UserRole } from '@/types';

vi.mock('@/services/adminAssessmentService', () => ({
  adminAssessmentService: { list: vi.fn(), listQuestionBank: vi.fn() },
}));
vi.mock('@/services/assessmentService', () => ({
  assessmentService: { list: vi.fn(), listSkills: vi.fn(), listSkillCategories: vi.fn() },
}));
vi.mock('@/services/studentService', () => ({
  studentService: { getProfile: vi.fn(), listDepartments: vi.fn() },
}));
vi.mock('@/services/readinessService', () => ({
  readinessService: { listRoles: vi.fn(), getLatest: vi.fn(), history: vi.fn(), compute: vi.fn(), gaps: vi.fn() },
}));
vi.mock('@/services/dashboardService', () => ({ dashboardService: { getStudent: vi.fn(), getPlacement: vi.fn() } }));
vi.mock('@/services/placementAnalyticsService', () => ({ placementAnalyticsService: { get: vi.fn() } }));
vi.mock('@/services/facultyDashboardService', () => ({ facultyDashboardService: { get: vi.fn() } }));
vi.mock('@/services/hodDashboardService', () => ({ hodDashboardService: { get: vi.fn() } }));
vi.mock('@/services/hodAssignmentService', () => ({ hodAssignmentService: { list: vi.fn(), create: vi.fn(), remove: vi.fn() } }));
vi.mock('@/services/adminReadinessService', () => ({
  adminReadinessService: { listRules: vi.fn(), listRoles: vi.fn() },
}));

import { adminAssessmentService } from '@/services/adminAssessmentService';
import { assessmentService } from '@/services/assessmentService';
import { adminReadinessService } from '@/services/adminReadinessService';
import { readinessService } from '@/services/readinessService';
import { studentService } from '@/services/studentService';
import { dashboardService } from '@/services/dashboardService';
import { facultyDashboardService } from '@/services/facultyDashboardService';
import { hodAssignmentService } from '@/services/hodAssignmentService';
import { hodDashboardService } from '@/services/hodDashboardService';
import { placementAnalyticsService } from '@/services/placementAnalyticsService';
import type { PlacementDashboard, StudentDashboard } from '@/types';

function renderAt(role: UserRole, path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthStub user={makeUser(role)}>
        <App />
      </AuthStub>
    </MemoryRouter>,
  );
}

const emptyStudent: StudentDashboard = {
  profile: { profile_complete: true, department_name: 'CSE', roll_number: 'R1' },
  rule_active: true,
  readiness: { general: null, roles: [] },
  skills: [],
  top_gaps: [],
  goals: [],
  plan: null,
  recent_assessments: [],
  not_implemented: [],
};
const emptyPlacement: PlacementDashboard = {
  generated_at: '2026-01-01T00:00:00Z',
  scope: { department_id: null, department_name: null },
  rule: null,
  rule_versions_in_use: [],
  totals: { students: 0, profile_complete: 0, with_readiness_score: 0, with_assessment_submitted: 0 },
  level_distribution: [],
  departments: [],
  top_gaps: [],
  assessment_participation: { published_assessments: 0, students_with_attempts: 0, submitted_attempts: 0 },
};

const completeProfile = {
  id: 1,
  user_id: 1,
  college_id: 1,
  department_id: 1,
  department_name: 'CSE',
  roll_number: 'R1',
  graduation_year: 2026,
  phone: '9876543210',
  profile_complete: true,
};

function mockNewDashboards(): void {
    vi.mocked(placementAnalyticsService.get).mockResolvedValue({
      generated_at: '2026-01-01T00:00:00Z',
      scope: { department_id: null, department_name: null },
      role_readiness: [],
      company_eligibility: [],
      progress_trends: [],
    });
    vi.mocked(facultyDashboardService.get).mockResolvedValue({
      generated_at: '2026-01-01T00:00:00Z',
      totals: { assigned_students: 0, with_readiness_score: 0, needing_support: 0 },
      students: [],
      top_gaps: [],
      assessment_performance: [],
    });
    vi.mocked(hodDashboardService.get).mockResolvedValue({
      generated_at: '2026-01-01T00:00:00Z',
      scope: { department_ids: [1], department_names: ['CSE'] },
      rule: null,
      rule_versions_in_use: [],
      totals: { students: 0, profile_complete: 0, with_readiness_score: 0, with_assessment_submitted: 0 },
      level_distribution: [],
      skill_heatmap: [],
      career_role_distribution: [],
      assessment_trends: [],
      training_priorities: [],
    });
    vi.mocked(hodAssignmentService.list).mockResolvedValue([]);
}

describe('dashboard routing', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(dashboardService.getStudent).mockResolvedValue(emptyStudent);
    vi.mocked(dashboardService.getPlacement).mockResolvedValue(emptyPlacement);
    vi.mocked(studentService.listDepartments).mockResolvedValue([]);
    vi.mocked(adminAssessmentService.list).mockResolvedValue([]);
    vi.mocked(studentService.getProfile).mockResolvedValue(completeProfile);
    mockNewDashboards();
  });

  it('sends a student from / to the dashboard with Dashboard as the first nav link', async () => {
    renderAt('STUDENT', '/');
    expect(await screen.findByRole('heading', { name: 'Your dashboard' })).toBeInTheDocument();
    const nav = screen.getByRole('navigation', { name: 'Main' });
    expect(within(nav).getAllByRole('link')[0]).toHaveTextContent('Dashboard');
  });

  it('keeps the onboarding gate for incomplete students', async () => {
    vi.mocked(studentService.getProfile).mockResolvedValue({ ...completeProfile, profile_complete: false });
    renderAt('STUDENT', '/');
    await waitFor(() => expect(studentService.getProfile).toHaveBeenCalled());
    expect(screen.queryByRole('heading', { name: 'Your dashboard' })).not.toBeInTheDocument();
    expect(dashboardService.getStudent).not.toHaveBeenCalled();
  });

  it('sends TPO from / to the placement dashboard', async () => {
    renderAt('TPO', '/');
    expect(await screen.findByRole('heading', { name: 'Placement dashboard' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Placement dashboard' })).toBeInTheDocument();
  });

  it('lets ADMIN open /placement and shows the nav link', async () => {
    renderAt('ADMIN', '/placement');
    expect(await screen.findByRole('heading', { name: 'Placement dashboard' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Placement dashboard' })).toBeInTheDocument();
  });

  it('sends ADMIN from / to /profile', async () => {
    renderAt('ADMIN', '/');
    expect(await screen.findByRole('heading', { name: 'Your profile' })).toBeInTheDocument();
  });

  it('sends FACULTY from / to the faculty dashboard with its nav link', async () => {
    renderAt('FACULTY', '/');
    expect(await screen.findByRole('heading', { name: 'Faculty dashboard' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Faculty dashboard' })).toBeInTheDocument();
  });

  it('sends HOD from / to the HOD dashboard and has no placement or admin links', async () => {
    renderAt('HOD', '/');
    expect(await screen.findByRole('heading', { name: 'HOD dashboard' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'HOD dashboard' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'HOD assignments' })).not.toBeInTheDocument();
    expect(dashboardService.getPlacement).not.toHaveBeenCalled();
    expect(hodAssignmentService.list).not.toHaveBeenCalled();
  });

  it('keeps non-faculty roles out of /faculty', () => {
    renderAt('STUDENT', '/faculty');
    renderAt('TPO', '/faculty');
    renderAt('ADMIN', '/faculty');
    renderAt('HOD', '/faculty');
    expect(facultyDashboardService.get).not.toHaveBeenCalled();
  });

  it('keeps non-HOD roles out of /hod and HOD assignments', () => {
    renderAt('STUDENT', '/hod');
    renderAt('TPO', '/hod');
    renderAt('ADMIN', '/hod');
    renderAt('FACULTY', '/admin/hod-assignments');
    renderAt('TPO', '/admin/hod-assignments');
    expect(hodDashboardService.get).not.toHaveBeenCalled();
    expect(hodAssignmentService.list).not.toHaveBeenCalled();
  });

  it('lets ADMIN open HOD assignments and shows the nav link', async () => {
    renderAt('ADMIN', '/admin/hod-assignments');
    expect(await screen.findByRole('heading', { name: 'HOD assignments', level: 1 })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'HOD assignments' })).toBeInTheDocument();
  });

  it('blocks students and faculty from /placement', () => {
    renderAt('STUDENT', '/placement');
    renderAt('FACULTY', '/placement');
    expect(dashboardService.getPlacement).not.toHaveBeenCalled();
  });

  it('blocks TPO from admin pages and the student dashboard', () => {
    renderAt('TPO', '/admin/assessments');
    renderAt('TPO', '/dashboard');
    expect(adminAssessmentService.list).not.toHaveBeenCalled();
    expect(dashboardService.getStudent).not.toHaveBeenCalled();
  });

  it('blocks ADMIN from the student dashboard', () => {
    renderAt('ADMIN', '/dashboard');
    expect(dashboardService.getStudent).not.toHaveBeenCalled();
  });
});

describe('role-gated assessment routes', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mockNewDashboards();
    vi.mocked(adminAssessmentService.list).mockResolvedValue([]);
    vi.mocked(adminAssessmentService.listQuestionBank).mockResolvedValue([]);
    vi.mocked(assessmentService.list).mockResolvedValue([]);
    vi.mocked(assessmentService.listSkills).mockResolvedValue([]);
    vi.mocked(assessmentService.listSkillCategories).mockResolvedValue([]);
    vi.mocked(studentService.listDepartments).mockResolvedValue([]);
    vi.mocked(readinessService.listRoles).mockResolvedValue([]);
    vi.mocked(readinessService.getLatest).mockRejectedValue(new Error('none'));
    vi.mocked(readinessService.history).mockResolvedValue([]);
    vi.mocked(adminReadinessService.listRules).mockResolvedValue([]);
    vi.mocked(adminReadinessService.listRoles).mockResolvedValue([]);
    vi.mocked(studentService.getProfile).mockResolvedValue({
      id: 1,
      user_id: 1,
      college_id: 1,
      department_id: 1,
      department_name: 'CSE',
      roll_number: 'R1',
      graduation_year: 2026,
      phone: '9876543210',
      profile_complete: true,
    });
  });

  it('lets FACULTY open admin assessments but sees no Skills nav link', async () => {
    renderAt('FACULTY', '/admin/assessments');
    expect(await screen.findByRole('heading', { name: 'Manage assessments' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Question bank' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Skills' })).not.toBeInTheDocument();
  });

  it('keeps FACULTY out of /admin/skills', () => {
    renderAt('FACULTY', '/admin/skills');
    expect(screen.queryByRole('heading', { name: 'Skills' })).not.toBeInTheDocument();
    expect(assessmentService.listSkillCategories).not.toHaveBeenCalled();
  });

  it('lets ADMIN open /admin/skills and shows the Skills link', async () => {
    renderAt('ADMIN', '/admin/skills');
    expect(await screen.findByRole('heading', { name: 'Skills', level: 1 })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Skills' })).toBeInTheDocument();
  });

  it('keeps students out of admin pages', () => {
    renderAt('STUDENT', '/admin/assessments');
    expect(screen.queryByRole('heading', { name: 'Manage assessments' })).not.toBeInTheDocument();
    expect(adminAssessmentService.list).not.toHaveBeenCalled();
  });

  it('keeps admins out of student assessment pages', () => {
    renderAt('ADMIN', '/assessments');
    expect(assessmentService.list).not.toHaveBeenCalled();
  });

  it('shows students the Assessments and History links', async () => {
    renderAt('STUDENT', '/assessments');
    expect(await screen.findByRole('heading', { name: 'Assessments' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'History' })).toBeInTheDocument();
  });

  it('shows students Readiness and Skill gaps links but no admin readiness links', async () => {
    renderAt('STUDENT', '/readiness');
    expect(await screen.findByRole('heading', { name: 'Placement readiness' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Skill gaps' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Readiness rules' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Career roles' })).not.toBeInTheDocument();
  });

  it('shows admins Readiness rules and Career roles links and the rules page', async () => {
    renderAt('ADMIN', '/admin/readiness-rules');
    expect(await screen.findByRole('heading', { name: 'Readiness rules', level: 1 })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Career roles' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Readiness' })).not.toBeInTheDocument();
  });

  it('keeps students out of admin readiness pages', () => {
    renderAt('STUDENT', '/admin/readiness-rules');
    expect(adminReadinessService.listRules).not.toHaveBeenCalled();
    renderAt('STUDENT', '/admin/career-roles');
    expect(adminReadinessService.listRoles).not.toHaveBeenCalled();
  });

  it('keeps admins and faculty out of student readiness pages', () => {
    renderAt('ADMIN', '/readiness');
    renderAt('FACULTY', '/readiness/gaps');
    expect(readinessService.listRoles).not.toHaveBeenCalled();
  });
});
