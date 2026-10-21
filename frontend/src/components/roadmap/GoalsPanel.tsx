import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { CareerGoal } from '@/types';

interface GoalsPanelProps {
  goals: CareerGoal[];
  dirty: boolean;
  saving: boolean;
  onMove: (index: number, direction: -1 | 1) => void;
  onRemove: (roleId: number) => void;
  onSave: () => void;
}

export function GoalsPanel({ goals, dirty, saving, onMove, onRemove, onSave }: GoalsPanelProps) {
  return (
    <Card aria-label="My goals">
      <CardHeader>
        <CardTitle className="text-lg">My goals</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {goals.length === 0 ? (
          <p className="text-sm text-muted-foreground">No goals yet. Star a role to add it here.</p>
        ) : (
          <ol className="space-y-2 text-sm" aria-label="Goal priority order">
            {goals.map((g, i) => (
              <li key={g.career_role_id} className="space-y-2 rounded-md border p-2">
                <div>
                  <span className="mr-2 font-semibold">{i + 1}.</span>
                  {g.role_name}
                </div>
                <div className="flex flex-wrap gap-1">
                  <Button variant="outline" size="sm" disabled={i === 0 || saving} onClick={() => onMove(i, -1)} aria-label={`Move ${g.role_name} up`}>
                    Up
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={i === goals.length - 1 || saving}
                    onClick={() => onMove(i, 1)}
                    aria-label={`Move ${g.role_name} down`}
                  >
                    Down
                  </Button>
                  <Button variant="ghost" size="sm" disabled={saving} onClick={() => onRemove(g.career_role_id)} aria-label={`Remove ${g.role_name}`}>
                    Remove
                  </Button>
                </div>
              </li>
            ))}
          </ol>
        )}
        <div className="flex items-center gap-3">
          <Button onClick={onSave} disabled={!dirty || saving}>
            {saving ? 'Saving...' : 'Save goals'}
          </Button>
          {dirty && <span className="text-xs text-muted-foreground">Unsaved changes</span>}
        </div>
      </CardContent>
    </Card>
  );
}
