import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FormMessage } from '@/components/auth/FormField';
import { Card, CardContent } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { getErrorMessage } from '@/lib/errors';
import { adminAssessmentService } from '@/services/adminAssessmentService';
import { assessmentService } from '@/services/assessmentService';
import { DIFFICULTIES, type AdminQuestion, type AssessmentSummary, type Difficulty, type QuestionBankFilters, type Skill } from '@/types';

const SELECT_CLASS =
  'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

export function QuestionBankPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [assessments, setAssessments] = useState<AssessmentSummary[]>([]);
  const [skillId, setSkillId] = useState('');
  const [difficulty, setDifficulty] = useState('');
  const [assessmentId, setAssessmentId] = useState('');
  const [questions, setQuestions] = useState<AdminQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([assessmentService.listSkills(), adminAssessmentService.list()])
      .then(([s, a]) => {
        if (cancelled) return;
        setSkills(s);
        setAssessments(a);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load filters.'));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const filters: QuestionBankFilters = {};
    if (skillId) filters.skill_id = Number(skillId);
    if (difficulty) filters.difficulty = difficulty as Difficulty;
    if (assessmentId) filters.assessment_id = Number(assessmentId);
    adminAssessmentService
      .listQuestionBank(filters)
      .then((q) => {
        if (cancelled) return;
        setQuestions(q);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(getErrorMessage(err, 'Could not load questions.'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [skillId, difficulty, assessmentId]);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-semibold">Question bank</h1>
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="f-skill">Skill</Label>
          <select id="f-skill" className={SELECT_CLASS} value={skillId} onChange={(e) => setSkillId(e.target.value)}>
            <option value="">All skills</option>
            {skills.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="f-difficulty">Difficulty</Label>
          <select id="f-difficulty" className={SELECT_CLASS} value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
            <option value="">All difficulties</option>
            {DIFFICULTIES.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="f-assessment">Assessment</Label>
          <select id="f-assessment" className={SELECT_CLASS} value={assessmentId} onChange={(e) => setAssessmentId(e.target.value)}>
            <option value="">All assessments</option>
            {assessments.map((a) => (
              <option key={a.id} value={a.id}>
                {a.title} (v{a.version})
              </option>
            ))}
          </select>
        </div>
      </div>
      <FormMessage message={error} />
      {loading && (
        <p role="status" className="text-muted-foreground">
          Loading questions...
        </p>
      )}
      {!loading && !error && questions.length === 0 && <p className="text-muted-foreground">No questions match these filters.</p>}
      <ul className="space-y-3">
        {questions.map((q) => (
          <li key={q.id}>
            <Card>
              <CardContent className="space-y-2 p-4 text-sm">
                <div className="font-medium">{q.body}</div>
                <div className="text-xs text-muted-foreground">
                  {q.skill_name} · {q.difficulty} · {q.marks} marks ·{' '}
                  <Link to={`/admin/assessments/${q.assessment_id}`} className="text-primary hover:underline">
                    Assessment #{q.assessment_id}
                  </Link>
                </div>
                <ul className="space-y-1">
                  {q.options.map((o) => (
                    <li key={o.id} className={q.correct_option_ids.includes(o.id) ? 'font-medium text-green-700' : ''}>
                      {o.text}
                      {q.correct_option_ids.includes(o.id) && ' (correct)'}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
