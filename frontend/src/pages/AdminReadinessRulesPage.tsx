import { useCallback, useEffect, useState } from 'react';
import { ConfirmPanel } from '@/components/assessment/ConfirmPanel';
import { FormMessage } from '@/components/auth/FormField';
import { RuleForm } from '@/components/readiness/RuleForm';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDate } from '@/lib/assessment';
import { getErrorMessage } from '@/lib/errors';
import { adminReadinessService } from '@/services/adminReadinessService';
import { assessmentService } from '@/services/assessmentService';
import type { ReadinessRule, ReadinessRuleInput, SkillCategory } from '@/types';

type FormState = { open: false } | { open: true; prefill: ReadinessRule | null };

export function AdminReadinessRulesPage() {
  const [rules, setRules] = useState<ReadinessRule[]>([]);
  const [categories, setCategories] = useState<SkillCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>({ open: false });
  const [saving, setSaving] = useState(false);
  const [activating, setActivating] = useState<ReadinessRule | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (): Promise<void> => {
    try {
      const [r, c] = await Promise.all([adminReadinessService.listRules(), assessmentService.listSkillCategories()]);
      setRules([...r].sort((a, b) => b.version - a.version));
      setCategories(c);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load readiness rules.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const categoryName = (id: string): string => categories.find((c) => String(c.id) === id)?.name ?? `Category ${id}`;
  const activeRule = rules.find((r) => r.is_active) ?? null;

  const handleCreate = async (payload: ReadinessRuleInput): Promise<void> => {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const created = await adminReadinessService.createRule(payload);
      setForm({ open: false });
      setNotice(`Version ${created.version} created. It is inactive until you activate it.`);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'Could not create the rule version.'));
    } finally {
      setSaving(false);
    }
  };

  const handleActivate = async (): Promise<void> => {
    if (!activating) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await adminReadinessService.activateRule(activating.id);
      setNotice(`Version ${activating.version} is now active.`);
      setActivating(null);
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'Could not activate the rule.'));
      setActivating(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Readiness rules</h1>
        {!form.open && (
          <Button onClick={() => setForm({ open: true, prefill: activeRule })}>Create new version</Button>
        )}
      </div>
      <p className="text-sm text-muted-foreground">Rules are immutable. To change scoring, create a new version and activate it.</p>
      <FormMessage message={error} />
      <FormMessage message={notice} tone="success" />

      {form.open && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              New version{form.prefill ? ` (prefilled from version ${form.prefill.version})` : ''}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <RuleForm
              key={form.prefill?.id ?? 'blank'}
              categories={categories}
              prefill={form.prefill}
              saving={saving}
              onSubmit={(p) => void handleCreate(p)}
              onCancel={() => setForm({ open: false })}
            />
          </CardContent>
        </Card>
      )}

      {activating && (
        <ConfirmPanel
          title="Activate this rule version?"
          message={`Version ${activating.version} will be used for all new readiness calculations${activeRule ? `, replacing version ${activeRule.version}` : ''}.`}
          confirmLabel="Activate"
          busy={busy}
          onConfirm={() => void handleActivate()}
          onCancel={() => setActivating(null)}
        />
      )}

      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading rules...
        </p>
      )}
      {!loading && rules.length === 0 && !error && <p className="text-muted-foreground">No readiness rules yet. Create the first version.</p>}
      <ul className="space-y-3">
        {rules.map((r) => (
          <li key={r.id}>
            <Card>
              <CardContent className="space-y-3 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">Version {r.version}</span>
                    {r.is_active && <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">Active</span>}
                    <span className="text-sm text-muted-foreground">{formatDate(r.created_at)}</span>
                  </div>
                  <div className="flex gap-2">
                    {!r.is_active && (
                      <Button size="sm" onClick={() => setActivating(r)} aria-label={`Activate version ${r.version}`}>
                        Activate
                      </Button>
                    )}
                    <Button size="sm" variant="outline" onClick={() => setForm({ open: true, prefill: r })} aria-label={`New version from version ${r.version}`}>
                      Use as template
                    </Button>
                  </div>
                </div>
                <dl className="grid gap-2 text-sm sm:grid-cols-3">
                  <div>
                    <dt className="font-medium">Weights</dt>
                    <dd className="text-muted-foreground">
                      {Object.entries(r.weights)
                        .map(([id, w]) => `${categoryName(id)}: ${w}`)
                        .join(', ') || 'None'}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-medium">Levels</dt>
                    <dd className="text-muted-foreground">{r.level_thresholds.map((t) => `${t.level} (from ${t.min_score})`).join(', ')}</dd>
                  </div>
                  <div>
                    <dt className="font-medium">Gap thresholds</dt>
                    <dd className="text-muted-foreground">
                      High from {r.gap_thresholds.high_min_gap}, medium from {r.gap_thresholds.medium_min_gap}
                    </dd>
                  </div>
                </dl>
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
