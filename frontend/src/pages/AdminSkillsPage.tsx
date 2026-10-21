import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { FieldError } from '@/components/auth/FieldError';
import { FormMessage } from '@/components/auth/FormField';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { getErrorMessage } from '@/lib/errors';
import { adminAssessmentService } from '@/services/adminAssessmentService';
import { DepartmentSelect, SELECT_CLASS } from '@/components/admin/DepartmentSelect';
import { assessmentService } from '@/services/assessmentService';
import { studentService } from '@/services/studentService';
import type { Department, Skill, SkillCategory, SkillCategoryScope } from '@/types';

export function AdminSkillsPage() {
  const [categories, setCategories] = useState<SkillCategory[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [catName, setCatName] = useState('');
  const [catScope, setCatScope] = useState<SkillCategoryScope>('COMMON');
  const [catDepartment, setCatDepartment] = useState('');
  const [departments, setDepartments] = useState<Department[]>([]);
  const [catEditId, setCatEditId] = useState<number | null>(null);
  const [catError, setCatError] = useState<string | undefined>();

  const [skillName, setSkillName] = useState('');
  const [skillDesc, setSkillDesc] = useState('');
  const [skillCategory, setSkillCategory] = useState('');
  const [skillEditId, setSkillEditId] = useState<number | null>(null);
  const [skillError, setSkillError] = useState<string | undefined>();
  const [saving, setSaving] = useState(false);

  const load = useCallback(async (): Promise<void> => {
    try {
      const [c, s, d] = await Promise.all([
        assessmentService.listSkillCategories(),
        assessmentService.listSkills(),
        studentService.listDepartments(),
      ]);
      setCategories(c);
      setSkills(s);
      setDepartments(d);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err, 'Could not load skills.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const resetCategory = (): void => {
    setCatName('');
    setCatScope('COMMON');
    setCatDepartment('');
    setCatEditId(null);
  };

  const resetSkill = (): void => {
    setSkillName('');
    setSkillDesc('');
    setSkillCategory('');
    setSkillEditId(null);
  };

  const submitCategory = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    if (!catName.trim()) {
      setCatError('Category name is required.');
      return;
    }
    if (catScope === 'DEPARTMENT' && !catDepartment) {
      setCatError('Select a department for a department-scoped category.');
      return;
    }
    setCatError(undefined);
    setSaving(true);
    setError(null);
    try {
      const payload = {
        name: catName.trim(),
        scope: catScope,
        department_id: catScope === 'DEPARTMENT' ? Number(catDepartment) : null,
      };
      if (catEditId !== null) await adminAssessmentService.updateCategory(catEditId, payload);
      else await adminAssessmentService.createCategory(payload);
      resetCategory();
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save the category.'));
    } finally {
      setSaving(false);
    }
  };

  const submitSkill = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    if (!skillName.trim() || !skillCategory) {
      setSkillError('Skill name and category are required.');
      return;
    }
    setSkillError(undefined);
    setSaving(true);
    setError(null);
    try {
      const payload = { category_id: Number(skillCategory), name: skillName.trim(), description: skillDesc.trim() || null };
      if (skillEditId !== null) await adminAssessmentService.updateSkill(skillEditId, payload);
      else await adminAssessmentService.createSkill(payload);
      resetSkill();
      await load();
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save the skill.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-semibold">Skills</h1>
      <FormMessage message={error} />
      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading skills...
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Categories</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <ul className="divide-y text-sm">
            {categories.map((c) => (
              <li key={c.id} className="flex items-center justify-between py-2">
                <span>
                  {c.name} <span className="text-muted-foreground">({c.scope})</span>
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setCatEditId(c.id);
                    setCatName(c.name);
                    setCatScope(c.scope);
                    setCatDepartment(c.department_id !== null ? String(c.department_id) : '');
                  }}
                  aria-label={`Edit category ${c.name}`}
                >
                  Edit
                </Button>
              </li>
            ))}
          </ul>
          <form onSubmit={(e) => void submitCategory(e)} noValidate className="grid gap-3 sm:grid-cols-2" aria-label="Category form">
            <div className="space-y-2">
              <Label htmlFor="cat-name">Category name</Label>
              <Input id="cat-name" value={catName} onChange={(e) => setCatName(e.target.value)} />
              <FieldError id="cat-name-error" message={catError} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="cat-scope">Scope</Label>
              <select
                id="cat-scope"
                className={SELECT_CLASS}
                value={catScope}
                onChange={(e) => {
                  const next = e.target.value as SkillCategoryScope;
                  setCatScope(next);
                  if (next === 'COMMON') setCatDepartment('');
                }}
              >
                <option value="COMMON">Common</option>
                <option value="DEPARTMENT">Department</option>
              </select>
            </div>
            {catScope === 'DEPARTMENT' && (
              <DepartmentSelect
                id="cat-department"
                label="Department (required)"
                departments={departments}
                value={catDepartment}
                onChange={setCatDepartment}
                placeholder="Select department"
                invalid={Boolean(catError)}
              />
            )}
            <div className="flex items-end gap-2">
              <Button type="submit" disabled={saving}>
                {catEditId !== null ? 'Save category' : 'Add category'}
              </Button>
              {catEditId !== null && (
                <Button type="button" variant="outline" onClick={resetCategory}>
                  Cancel
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Skills</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <ul className="divide-y text-sm">
            {skills.map((s) => (
              <li key={s.id} className="flex items-center justify-between py-2">
                <span>
                  {s.name} <span className="text-muted-foreground">({s.category_name})</span>
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setSkillEditId(s.id);
                    setSkillName(s.name);
                    setSkillDesc(s.description ?? '');
                    setSkillCategory(String(s.category_id));
                  }}
                  aria-label={`Edit skill ${s.name}`}
                >
                  Edit
                </Button>
              </li>
            ))}
          </ul>
          <form onSubmit={(e) => void submitSkill(e)} noValidate className="grid gap-3 sm:grid-cols-2" aria-label="Skill form">
            <div className="space-y-2">
              <Label htmlFor="skill-name">Skill name</Label>
              <Input id="skill-name" value={skillName} onChange={(e) => setSkillName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="skill-category">Category</Label>
              <select id="skill-category" className={SELECT_CLASS} value={skillCategory} onChange={(e) => setSkillCategory(e.target.value)}>
                <option value="">Select category</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="skill-desc">Description (optional)</Label>
              <Input id="skill-desc" value={skillDesc} onChange={(e) => setSkillDesc(e.target.value)} />
              <FieldError id="skill-error" message={skillError} />
            </div>
            <div className="flex gap-2 sm:col-span-2">
              <Button type="submit" disabled={saving}>
                {skillEditId !== null ? 'Save skill' : 'Add skill'}
              </Button>
              {skillEditId !== null && (
                <Button type="button" variant="outline" onClick={resetSkill}>
                  Cancel
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
