import { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { Brand } from './Brand';
import { PageWrapper } from './PageWrapper';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';
import type { UserRole } from '@/types';

interface NavItem {
  to: string;
  label: string;
}

interface NavGroup {
  title: string;
  links: NavItem[];
}

const PROFILE_LINK: NavItem = { to: '/profile', label: 'Profile' };
const KNOWLEDGE_SEARCH_LINK: NavItem = { to: '/knowledge', label: 'Knowledge search' };
const KNOWLEDGE_ADMIN_LINK: NavItem = { to: '/admin/knowledge', label: 'Knowledge base' };
const MCP_TOOLS_LINK: NavItem = { to: '/admin/mcp-tools', label: 'MCP tools' };
// Who sees the guide link mirrors GUIDE_ROLES in backend/app/services/guide_service.py (ADMIN only for now).
const GUIDE_LINK: NavItem = { to: '/guide', label: 'User guide' };
const PLACEMENT_LINK: NavItem = { to: '/placement', label: 'Placement dashboard' };
const FACULTY_LINK: NavItem = { to: '/faculty', label: 'Faculty dashboard' };
const HOD_LINK: NavItem = { to: '/hod', label: 'HOD dashboard' };
const USERS_LINK: NavItem = { to: '/admin/users', label: 'Users and students' };
const HOD_ASSIGNMENTS_LINK: NavItem = { to: '/admin/hod-assignments', label: 'HOD assignments' };

const JOB_ADMIN_LINKS: NavItem[] = [
  { to: '/admin/companies', label: 'Companies' },
  { to: '/admin/jobs', label: 'Jobs' },
];

const STAFF_LINKS: NavItem[] = [
  { to: '/admin/assessments', label: 'Assessments' },
  { to: '/admin/question-bank', label: 'Question bank' },
  { to: '/admin/learning-resources', label: 'Learning resources' },
  { to: '/admin/interview-questions', label: 'Interview questions' },
];

const ADMIN_ONLY_LINKS: NavItem[] = [
  { to: '/admin/skills', label: 'Skills' },
  { to: '/admin/readiness-rules', label: 'Readiness rules' },
  { to: '/admin/career-roles', label: 'Career roles' },
];

const STUDENT_GROUPS: NavGroup[] = [
  {
    title: 'Overview',
    links: [
      { to: '/dashboard', label: 'Dashboard' },
      { to: '/assistant', label: 'Assistant' },
    ],
  },
  {
    title: 'My profile',
    links: [
      { to: '/profile', label: 'Profile' },
      { to: '/profile/academics', label: 'Academics' },
      { to: '/profile/projects', label: 'Projects & Certifications' },
    ],
  },
  {
    title: 'Skills and readiness',
    links: [
      { to: '/assessments', label: 'Assessments' },
      { to: '/assessments/history', label: 'History' },
      { to: '/readiness', label: 'Readiness' },
      { to: '/readiness/gaps', label: 'Skill gaps' },
    ],
  },
  {
    title: 'Career',
    links: [
      { to: '/careers', label: 'Careers' },
      { to: '/plan', label: 'Plan' },
      { to: '/interview', label: 'Interview' },
      { to: '/resume', label: 'Resume' },
    ],
  },
  {
    title: 'Jobs and knowledge',
    links: [
      { to: '/jobs', label: 'Jobs' },
      { to: '/knowledge', label: 'Knowledge' },
    ],
  },
];

function groupsForRole(role: UserRole | undefined): NavGroup[] {
  if (role === 'STUDENT') return STUDENT_GROUPS;
  if (role === 'TPO') {
    return [
      { title: 'Placement', links: [PLACEMENT_LINK, ...JOB_ADMIN_LINKS] },
      { title: 'General', links: [PROFILE_LINK, KNOWLEDGE_SEARCH_LINK] },
    ];
  }
  if (role === 'ADMIN') {
    return [
      { title: 'Placement', links: [PLACEMENT_LINK, ...JOB_ADMIN_LINKS] },
      { title: 'Assessment content', links: STAFF_LINKS },
      { title: 'College setup', links: [USERS_LINK, ...ADMIN_ONLY_LINKS, HOD_ASSIGNMENTS_LINK] },
      { title: 'Knowledge', links: [KNOWLEDGE_ADMIN_LINK, MCP_TOOLS_LINK, KNOWLEDGE_SEARCH_LINK] },
      { title: 'Help', links: [GUIDE_LINK] },
    ];
  }
  if (role === 'HOD') return [{ title: 'Department', links: [HOD_LINK, PROFILE_LINK, KNOWLEDGE_SEARCH_LINK] }];
  if (role === 'FACULTY') {
    return [
      { title: 'My students', links: [FACULTY_LINK] },
      { title: 'Assessment content', links: STAFF_LINKS },
      { title: 'Knowledge', links: [KNOWLEDGE_ADMIN_LINK, KNOWLEDGE_SEARCH_LINK] },
    ];
  }
  return [];
}

const LINK_BASE = 'block rounded-md px-3 py-1.5 text-sm';
const LINK_ACTIVE = `${LINK_BASE} bg-primary font-medium text-primary-foreground`;
const LINK_IDLE = `${LINK_BASE} text-muted-foreground hover:bg-accent hover:text-foreground`;

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const groups = groupsForRole(user?.role);
  const [loggingOut, setLoggingOut] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = async (): Promise<void> => {
    setLoggingOut(true);
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="min-h-screen bg-muted/40 md:flex">
      <header className="flex items-center justify-between border-b bg-background px-4 py-2 md:hidden">
        <Brand />
        <Button
          variant="outline"
          size="sm"
          aria-expanded={menuOpen}
          aria-controls="app-sidebar"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? <X className="h-4 w-4" aria-hidden="true" /> : <Menu className="h-4 w-4" aria-hidden="true" />}
          <span className="ml-2">{menuOpen ? 'Close menu' : 'Menu'}</span>
        </Button>
      </header>

      <aside
        id="app-sidebar"
        className={`${menuOpen ? 'flex' : 'hidden'} flex-col border-b bg-background md:sticky md:top-0 md:flex md:h-screen md:w-64 md:shrink-0 md:border-b-0 md:border-r`}
      >
        <div className="hidden px-4 py-4 md:block">
          <Brand />
        </div>
        <nav aria-label="Main" className="flex-1 space-y-5 overflow-y-auto px-3 py-3 md:py-2">
          {groups.map((group) => (
            <div key={group.title}>
              <h2 className="mb-1 px-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{group.title}</h2>
              <ul className="space-y-0.5">
                {group.links.map((link) => (
                  <li key={link.to}>
                    <NavLink
                      to={link.to}
                      end
                      onClick={() => setMenuOpen(false)}
                      className={({ isActive }) => (isActive ? LINK_ACTIVE : LINK_IDLE)}
                    >
                      {link.label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
        <div className="flex items-center justify-between gap-3 border-t px-4 py-3">
          {user && (
            <div className="min-w-0 text-sm leading-tight">
              <div className="truncate font-medium">{user.full_name}</div>
              <div className="text-xs text-muted-foreground">{user.role}</div>
            </div>
          )}
          <Button variant="outline" size="sm" onClick={handleLogout} disabled={loggingOut}>
            {loggingOut ? 'Signing out...' : 'Log out'}
          </Button>
        </div>
      </aside>

      <main className="min-w-0 flex-1 px-4 py-8 md:px-8">
        <div className="mx-auto max-w-5xl">
          <PageWrapper>
            <Outlet />
          </PageWrapper>
        </div>
      </main>
    </div>
  );
}
