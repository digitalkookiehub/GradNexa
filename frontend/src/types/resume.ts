export interface Resume {
  id: number;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  page_count: number | null;
  uploaded_at: string;
  has_text: boolean;
  text_length: number;
}

export interface ResumeText {
  text: string;
}

export interface Span {
  start: number;
  end: number;
  text: string;
}

export interface Block {
  text: string;
  span: Span;
}

export interface ExtractedSkill {
  skill_id: number;
  skill_name: string;
  spans: Span[];
}

export interface Extracted {
  sections_found: string[];
  skills: ExtractedSkill[];
  education: Block[];
  projects: Block[];
  experience: Block[];
  certifications: Block[];
}

export interface RoleSkillRef {
  skill_id: number;
  skill_name: string;
  required_level: number;
  weight: number;
}

export interface RoleMatch {
  match_percent: number | null;
  found: RoleSkillRef[];
  missing: RoleSkillRef[];
}

export interface JdSkill {
  skill_id: number;
  skill_name: string;
  in_resume: boolean;
}

export interface JdMatch {
  match_percent: number | null;
  skills_in_jd: JdSkill[];
}

export interface ResumeAnalysis {
  id: number;
  resume_id: number;
  role_id: number | null;
  role_name: string | null;
  job_id?: number | null;
  job_title?: string | null;
  extractor_version: string;
  created_at: string;
  extracted: Extracted;
  role_match: RoleMatch | null;
  jd_match: JdMatch | null;
  notes: string[];
}

export interface AnalysisSummary {
  id: number;
  created_at: string;
  role_name: string | null;
  has_jd: boolean;
  role_match_percent: number | null;
}

export interface AnalyzePayload {
  role_id?: number;
  jd_text?: string;
  job_id?: number;
}
