export type InterviewStatus = 'IN_PROGRESS' | 'COMPLETED';

export interface InterviewQuestion {
  answer_id: number;
  question_id: number;
  position: number;
  competency: string;
  prompt: string;
  min_words: number;
  answer_text: string | null;
}

export interface Interview {
  id: number;
  role_id: number;
  role_name: string;
  status: InterviewStatus;
  started_at: string;
  completed_at: string | null;
  questions: InterviewQuestion[];
}

export interface InterviewSummary {
  id: number;
  role_id: number;
  role_name: string;
  status: InterviewStatus;
  started_at: string;
  completed_at: string | null;
  overall: number | null;
}

export interface InterviewAnswerInput {
  answer_id: number;
  answer_text: string;
}

export interface CompetencyScore {
  competency: string;
  score: number;
  max: number;
  questions: number;
}

export interface QuestionResult {
  question_id: number;
  position: number;
  prompt: string;
  competency: string;
  score: number;
  answered: boolean;
  too_short: boolean;
  covered_concepts: string[];
  missed_concepts: string[];
}

export interface InterviewResult {
  id: number;
  interview_id: number;
  role_name: string;
  overall: number | null;
  competency_scores: CompetencyScore[];
  per_question: QuestionResult[];
  computed_at: string;
  scoring_version: string | number;
  disclaimer: string;
}

export interface RubricConcept {
  concept: string;
  keywords: string[];
  weight: number;
}

export interface BankQuestion {
  id: number;
  role_id: number | null;
  role_name: string | null;
  skill_id: number | null;
  competency: string;
  prompt: string;
  rubric: RubricConcept[];
  min_words: number;
  is_active: boolean;
  created_by: number | null;
}

export interface BankQuestionInput {
  role_id: number | null;
  skill_id: number | null;
  competency: string;
  prompt: string;
  rubric: RubricConcept[];
  min_words: number;
}

export interface BankQuestionFilter {
  role_id?: number | null;
  active?: boolean | null;
}

export interface DashboardResume {
  resume_id: number;
  filename: string;
  analyzed_at: string | null;
  role_name: string | null;
  role_match_percent: number | null;
}

export interface DashboardInterview {
  completed_count: number;
  latest: { role_name: string; overall: number | null; computed_at: string } | null;
}
