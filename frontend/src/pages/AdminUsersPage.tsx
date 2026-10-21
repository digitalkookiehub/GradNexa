import { useState } from 'react';
import { FacultyAssignmentsTab } from '@/components/adminUsers/FacultyAssignmentsTab';
import { UsersTab } from '@/components/adminUsers/UsersTab';

type Tab = 'users' | 'faculty';

const TABS: { id: Tab; label: string }[] = [
  { id: 'users', label: 'Users and students' },
  { id: 'faculty', label: 'Faculty assignments' },
];

export function AdminUsersPage() {
  const [tab, setTab] = useState<Tab>('users');
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Users and students</h1>
        <p className="text-sm text-muted-foreground">
          Everyone registered in your college. Change a user's role to create faculty, TPO, HOD or admin accounts, and assign students to faculty.
        </p>
      </div>
      <div role="tablist" aria-label="Users sections" className="flex flex-wrap gap-2 border-b pb-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            id={`users-tab-${t.id}`}
            aria-selected={tab === t.id}
            aria-controls={`users-panel-${t.id}`}
            className={tab === t.id ? 'rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground' : 'rounded-md border px-3 py-1.5 text-sm hover:bg-accent'}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`users-panel-${tab}`} aria-labelledby={`users-tab-${tab}`}>
        {tab === 'users' ? <UsersTab /> : <FacultyAssignmentsTab />}
      </div>
    </div>
  );
}
