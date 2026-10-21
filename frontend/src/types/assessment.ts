export type AssessmentType = 'APTITUDE' | 'TECHNICAL' | 'COMMUNICATION' | 'ROLE_SPECIFIC' | 'DEPARTMENT_SPECIFIC' | 'CUSTOM';
export type AssessmentStatus = 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';
export type AttemptStatus = 'IN_PROGRESS' | 'SUBMITTED' | 'EXPIRED';
export type Difficulty = 'EASY' | 'MEDIUM' | 'HARD';
export type SkillCategoryScope = 'COMMON' | 'DEPARTMENT';

export const ASSESSMENT_TYPES: AssessmentType[] = [
  'APTITUDE',
  'TECHNICAL',
  'COMMUNICATION',
  'ROLE_SPECIFIC',
  'DEPARTMENT_SPECIFIC',
  'CUSTOM',
];
export const DIFFICULTIES: Difficulty[] = ['EASY', 'MEDIUM', 'HARD'];

export interface Option {
  id: string;
  text: string;
}

export interface AssessmentSummary {
  id: number;
  series_key: string;
  version: number;
  title: string;
  type: AssessmentType;
  department_id: number | null;
  time_limit_min: number | null;
  max_attempts: number | null;
  negative_marking: number;
  status: AssessmentStatus;
  question_count: number;
  total_marks: number;
}

export interface StudentAssessment extends AssessmentSummary {
  attempts_used: number;
  in_progress_attempt_id: number | null;
}

export interface AttemptQuestion {
  id: number;
  body: string;
  options: Option[];
  marks: number;
  position: number;
  skill_id: number;
  skill_name: string;
  multi_select: boolean;
}

export type AnswerMap = Record<string, string[]>;

export interface Attempt {
  id: number;
  assessment_id: number;
  attempt_no: number;
  status: AttemptStatus;
  started_at: string;
  expires_at: string | null;
  questions: AttemptQuestion[];
  answers: AnswerMap;
}

export interface SkillScore {
  skill_id: number;
  skill_name: string;
  score: number;
  max: number;
  percentage: number;
}

export interface AssessmentResult {
  id: number;
  attempt_id: number;
  assessment_id: number;
  assessment_title: string;
  assessment_version: number;
  total_score: number;
  max_score: number;
  percentage: number;
  per_skill_scores: SkillScore[];
  computed_at: string;
}

export interface HistoryEntry extends AssessmentResult {
  submitted_at: string;
  attempt_no: number;
}

export interface StudentSkill {
  skill_id: number;
  skill_name: string;
  category_name: string;
  score: number;
  evidence_count: number;
  confidence: number | null;
  updated_at: string;
}

export interface Skill {
  id: number;
  name: string;
  description: string | null;
  category_id: number;
  category_name: string;
}

export interface SkillCategory {
  id: number;
  name: string;
  scope: SkillCategoryScope;
  department_id: number | null;
}

export interface AdminQuestion {
  id: number;
  assessment_id: number;
  skill_id: number;
  skill_name: string;
  difficulty: Difficulty;
  body: string;
  options: Option[];
  correct_option_ids: string[];
  marks: number;
  position: number;
}

export interface AdminAssessmentDetail extends AssessmentSummary {
  created_by: number | null;
  questions: AdminQuestion[];
}

export interface AssessmentInput {
  title: string;
  type: AssessmentType;
  department_id?: number | null;
  time_limit_min?: number | null;
  max_attempts?: number | null;
  negative_marking?: number;
}

export interface QuestionInput {
  skill_id: number;
  difficulty: Difficulty;
  body: string;
  options: Option[];
  correct_option_ids: string[];
  marks?: number;
  position?: number;
}

export interface SkillCategoryInput {
  name: string;
  scope: SkillCategoryScope;
  department_id?: number | null;
}

export interface SkillInput {
  category_id: number;
  name: string;
  description?: string | null;
}

export interface QuestionBankFilters {
  skill_id?: number;
  difficulty?: Difficulty;
  assessment_id?: number;
}

export interface AssessmentFilters {
  status?: AssessmentStatus;
  type?: AssessmentType;
}
