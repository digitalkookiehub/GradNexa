export interface GuideStep {
  do: string;
  detail?: string | null;
  expect?: string | null;
}

export interface GuideProblem {
  problem: string;
  fix: string;
}

export interface GuideTerm {
  term: string;
  meaning: string;
}

export interface GuideTable {
  title: string;
  columns: string[];
  rows: string[][];
  caption?: string | null;
}

export interface GuideProcedure {
  id: string;
  title: string;
  audience: string;
  path: string | null;
  summary: string;
  before: string[];
  steps: GuideStep[];
  result: string[];
  problems: GuideProblem[];
  terms: GuideTerm[];
  tables: GuideTable[];
  note?: string | null;
  next?: string | null;
}

export interface GuideGroup {
  id: string;
  title: string;
  intro?: string | null;
  procedures: GuideProcedure[];
}

export interface GuideRole {
  role: string;
  does: string;
  lands: string;
}

export interface GuideOverviewItem {
  id: string;
  title: string;
  summary: string;
  goto: string;
}

export interface Guide {
  title: string;
  tagline: string;
  principles: string[];
  roles: GuideRole[];
  overview: GuideOverviewItem[];
  groups: GuideGroup[];
  markdown: string;
}
