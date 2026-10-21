export type GapStatus = 'READY' | 'GAP' | 'NO_EVIDENCE';
export type GapPriority = 'NONE' | 'LOW' | 'MEDIUM' | 'HIGH' | 'UNASSESSED';

export interface Gap {
  skill_id: number;
  skill_name: string;
  current: number | null;
  required: number;
  gap: number | null;
  status: GapStatus;
  priority: GapPriority;
  recommended_action: string;
}

export interface CategoryScore {
  category_id: number;
  category_name: string;
  weight: number;
  score: number | null;
  evidence_count: number;
}

export interface EvidenceItem {
  skill_id: number;
  skill_name: string;
  category_name: string;
  score: number;
  evidence_count: number;
  last_result_id: number | null;
}

export interface ReadinessResult {
  id: number;
  student_id: number;
  role_id: number | null;
  role_name: string | null;
  rule_id: number;
  rule_version: number;
  overall: number | null;
  level: string | null;
  coverage: number;
  category_scores: CategoryScore[];
  evidence: EvidenceItem[];
  gaps: Gap[];
  computed_at: string;
}

export interface CareerRole {
  id: number;
  department_id: number | null;
  name: string;
  description: string | null;
  is_active: boolean;
}

export interface RoleSkill {
  skill_id: number;
  skill_name: string;
  required_level: number;
  weight: number;
}

export interface CareerRoleDetail extends CareerRole {
  skills: RoleSkill[];
}

export interface CareerRoleInput {
  name: string;
  description?: string | null;
  department_id?: number | null;
  is_active?: boolean;
}

export interface RoleSkillInput {
  skill_id: number;
  required_level: number;
  weight: number;
}

export interface LevelThreshold {
  level: string;
  min_score: number;
}

export interface GapThresholds {
  high_min_gap: number;
  medium_min_gap: number;
}

export interface ReadinessRule {
  id: number;
  version: number;
  is_active: boolean;
  weights: Record<string, number>;
  level_thresholds: LevelThreshold[];
  gap_thresholds: GapThresholds;
  created_by: number | null;
  created_at: string;
}

export interface ReadinessRuleInput {
  weights: Record<string, number>;
  level_thresholds: LevelThreshold[];
  gap_thresholds: GapThresholds;
}
