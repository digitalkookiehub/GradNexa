# PRP: GradNexa

> Implementation blueprint for phased, agent-driven execution

---

## METADATA

| Field | Value |
|-------|-------|
| **Product** | GradNexa - Engineering Career Intelligence Platform |
| **Type** | SaaS (multi-tenant, one tenant per college) |
| **Version** | 1.0 |
| **Created** | 2026-10-15 |
| **Complexity** | High |
| **Sources** | `INITIAL.md`, `CLAUDE.md`, `requirement docs/AI_Engineering_Career_Intelligence_All_Departments_Master_Product_Development_Prompt.txt` |

---

## PRODUCT OVERVIEW

**Description:** A unified platform for engineering colleges that tells each student where they stand, which career roles fit, which skills are missing and what to do next, using evidence-based assessment, deterministic readiness scoring and skill-gap analysis. It supports all engineering departments through database-driven configuration.

**Value Proposition:** Colleges get explainable, auditable placement-readiness intelligence per student, department and role. Students get a concrete, evidence-grounded path from graduate to industry-ready. It is not a chatbot and never predicts placement probability.

**MVP Scope** (master prompt Section 30):
- [ ] Authentication, RBAC, tenant isolation
- [ ] College and configurable departments
- [ ] Student and academic profile
- [ ] Career role selection
- [ ] Resume analysis
- [ ] Assessments with deterministic scoring
- [ ] Deterministic, versioned readiness score
- [ ] Skill-gap analysis
- [ ] Personalized 30-day plan
- [ ] Student dashboard
- [ ] Basic placement officer dashboard

**Post-MVP (in order):** RAG, MCP, AI orchestration, mock interviews, advanced analytics (faculty, HOD, full placement).

---

## NON-NEGOTIABLE RULES (apply to every agent)

1. No hard-coded department, skill, role or rule logic; all of it is data.
2. Scores are computed by deterministic code. The LLM never produces or changes a number.
3. Eligibility and readiness are separate outputs and never merged.
4. No placement-probability language. Use levels ("Strong", "Needs improvement") and "meets configured eligibility criteria".
5. Every score stores rule version plus evidence.
6. No fabricated data (results, scores, citations, MCP responses, resume facts). Unbuilt features respond "Not implemented in this phase."
7. Unknown business rules become open questions (see `INITIAL.md`) and configurable settings, not invented policy.
8. Every query is scoped by `college_id`; students see only their own data, faculty only assigned students.
9. **Stop after every product phase** with the Section 25 report and wait for approval.

---

## TECH STACK

| Layer | Technology | Skill Reference |
|-------|------------|-----------------|
| Backend | FastAPI + Python 3.11+ | skills/BACKEND.md |
| Frontend | React + TypeScript + Vite | skills/FRONTEND.md |
| Database | PostgreSQL + SQLAlchemy + Alembic (pgvector for RAG later) | skills/DATABASE.md |
| Auth | Email/Password, JWT access + refresh, bcrypt, RBAC | skills/BACKEND.md |
| UI | Tailwind CSS + shadcn/ui | skills/FRONTEND.md |
| Testing | pytest + React Testing Library | skills/TESTING.md |
| Deployment | Docker + GitHub Actions | skills/DEPLOYMENT.md |
| AI (post-MVP) | Configurable LLM provider, pgvector, FastMCP | - |

---

## DATABASE MODELS (37)

All tenant-owned tables carry `college_id`.

### Identity & platform
- **College**: id, name, code, is_active, created_at
- **User**: id, college_id, email, hashed_password, full_name, role (STUDENT/FACULTY/TPO/HOD/ADMIN/SUPER_ADMIN), is_active, is_verified, created_at
- **RefreshToken**: id, user_id, token_hash, expires_at, revoked
- **PasswordResetToken**: id, user_id, token_hash, expires_at, used
- **AuditLog**: id, college_id, user_id, action, resource, resource_id, metadata (JSON), created_at

### Profile (Phase 1)
- **Department**: id, college_id, name, code, is_active
- **Student**: id, user_id, college_id, department_id, roll_number, graduation_year, phone
- **AcademicRecord**: id, student_id, semester, cgpa, active_arrears, attendance_pct
- **Project**: id, student_id, title, description, skills, url
- **Certification**: id, student_id, name, issuer, issued_on
- **FacultyAssignment**: id, faculty_user_id, student_id (assignment model is an open question)
- **StudentCareerGoal**: id, student_id, career_role_id, priority

### Skills & assessment (Phase 2)
- **SkillCategory**: id, college_id, name, scope (COMMON/DEPARTMENT), department_id (nullable)
- **Skill**: id, college_id, category_id, name, description
- **Assessment**: id, college_id, title, type, version, time_limit_min, max_attempts, negative_marking, status
- **AssessmentQuestion**: id, assessment_id, skill_id, difficulty, body, options (JSON), answer_key, marks
- **AssessmentAttempt**: id, assessment_id, student_id, started_at, submitted_at, answers (JSON)
- **AssessmentResult**: id, attempt_id, total_score, per_skill_scores (JSON), assessment_version
- **StudentSkill**: id, student_id, skill_id, score, confidence, evidence_ref, updated_at

### Readiness (Phase 3)
- **ReadinessRule**: id, college_id, version, weights (JSON), level_thresholds (JSON), is_active
- **ReadinessScore**: id, student_id, role_id (nullable), rule_version, overall, category_scores (JSON), level, evidence (JSON), computed_at
- **SkillGap**: id, student_id, role_id, skill_id, current, required, gap, priority, recommended_action, computed_at

### Careers & plan (Phase 4)
- **CareerRole**: id, college_id, department_id, name, description
- **RoleSkill**: id, role_id, skill_id, required_level, weight
- **LearningResource**: id, college_id, skill_id, title, url, approved_by, approved_at
- **LearningPlan**: id, student_id, role_id, starts_on, status
- **LearningPlanItem**: id, plan_id, week, skill_id, resource_id, task, status

### Resume & interview (Phase 6)
- **Resume**: id, student_id, file_ref, mime_type, uploaded_at
- **ResumeAnalysis**: id, resume_id, extracted (JSON), missing_skills, role_match (JSON), source_spans (JSON), created_at
- **MockInterview**: id, student_id, role_id, status, started_at
- **InterviewResult**: id, interview_id, competency_scores (JSON), feedback

### Jobs (Phase 7)
- **Company**: id, college_id, name, description
- **JobDescription**: id, company_id, role_id (nullable), title, body, skills_required
- **EligibilityRule**: id, job_id, cgpa_min, max_arrears, attendance_min, department_ids, graduation_year, custom (JSON)

### AI layer (Phase 8)
- **RAGDocument**: id, college_id, title, source_type, status, uploaded_by
- **RAGChunk**: id, document_id, content, metadata (JSON), embedding (vector)
- **MCPTool**: id, name, description, input_schema, output_schema, is_enabled

---

## MODULES

### Module 0: Foundation & Authentication
**Agents:** DATABASE + BACKEND + FRONTEND + DEVOPS

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/register | Create account |
| POST | /api/v1/auth/login | Get tokens |
| POST | /api/v1/auth/refresh | Refresh token |
| POST | /api/v1/auth/logout | Revoke refresh token |
| POST | /api/v1/auth/forgot-password | Send reset email |
| POST | /api/v1/auth/reset-password | Reset with token |
| GET/PUT | /api/v1/auth/me | Current user profile |
| GET | /health, /health/ready | Health checks |

| Route | Page | Components |
|-------|------|------------|
| /login, /register | LoginPage, RegisterPage | AuthForm |
| /forgot-password, /reset-password | ForgotPasswordPage, ResetPasswordPage | AuthForm |
| /profile | ProfilePage (protected) | ProfileForm |

Also: RBAC dependency (`require_role`), tenant-scoping dependency, audit logging, rate limiting, structured logging, error handlers, test framework.

### Module 1 (Phase 1): Student & Academic Profile
**Endpoints:** GET/PUT `/students/me`; GET/POST/PUT `/students/me/academic-records`; GET/POST/DELETE `/students/me/projects`; GET/POST/DELETE `/students/me/certifications`; GET/PUT `/students/me/career-goals`; GET `/students/{id}` (faculty/TPO/HOD, scoped); GET `/departments`.
**Pages:** /onboarding (profile → academics → department → career goals), /profile/academics, /profile/projects.

### Module 2 (Phase 2): Skill Assessment
**Endpoints:** GET `/assessments`, GET `/assessments/{id}`, POST `/assessments/{id}/attempts`, PUT `/attempts/{id}/answers`, POST `/attempts/{id}/submit`, GET `/attempts/{id}/result`, GET `/assessments/history`; admin/faculty: POST/PUT/DELETE `/admin/assessments`, POST `/admin/assessments/{id}/publish`, CRUD `/admin/question-bank`.
**Pages:** /assessments, /assessments/{id}/attempt, /assessments/{id}/result, /assessments/history, /admin/question-bank.
**Rules:** deterministic scoring, negative marking if configured, versioned assessments, attempt limits and time limits enforced server-side.

### Module 3 (Phase 3): Readiness & Skill Gap Engine
**Endpoints:** POST `/readiness/compute`, GET `/readiness/me`, GET `/readiness/me/history`, GET `/readiness/gaps?role_id=`, GET `/readiness/{student_id}` (staff, scoped); admin GET/POST/PUT `/admin/readiness-rules` (new version on change).
**Pages:** /readiness, /readiness/gaps.
**Rules:** gap = max(required − current, 0); priority from configurable thresholds; evidence listed per category.

### Module 4 (Phase 4): Career Explorer & Roadmap
**Endpoints:** GET `/career-roles`, GET `/career-roles/{id}`; admin CRUD `/admin/career-roles`, `/admin/role-skills`, `/admin/skills`, `/admin/skill-categories`, `/admin/departments`, `/admin/learning-resources`; POST `/plans/generate`, GET `/plans/me`, PATCH `/plans/items/{id}`, POST `/plans/me/reassess`.
**Pages:** /careers, /careers/{id}, /plan, /plan/progress, plus admin configuration pages.
**Rules:** plan built only from configured skills, approved resources and assessment evidence.

### Module 5 (Phase 5): Student Dashboard
**Endpoints:** GET `/dashboard/student` (aggregates readiness, skills, gaps, plan, history, resume score).
**Pages:** /dashboard, /settings.

### Module 6 (Phase 6): Resume & Interview Intelligence
**Endpoints:** POST/GET `/resumes`, DELETE `/resumes/{id}`, POST `/resumes/{id}/analyze`, GET `/resumes/{id}/analysis`, POST `/resumes/{id}/compare` (role or JD); interview (post-MVP): POST `/interviews`, POST `/interviews/{id}/answers`, POST `/interviews/{id}/finish`, GET `/interviews/{id}/result`.
**Pages:** /resume, /resume/{id}/analysis, /interview, /interview/{id}/result.
**Rules:** secure upload (type, size, content checks); no fabricated facts; extracted items link to source spans.

### Module 7 (Phase 7): Job & Company Matching
**Endpoints:** CRUD `/admin/companies`, CRUD `/admin/jobs`, GET `/jobs`, GET `/jobs/{id}`, GET `/jobs/{id}/eligibility`.
**Pages:** /jobs, /jobs/{id}, /admin/companies.
**Rules:** eligibility shown separately from readiness.

### Module 8 (Phase 8): RAG + MCP + Advanced Analytics (post-MVP)
**Endpoints:** CRUD `/admin/knowledge-documents`, POST `/assistant/query`, MCP server with read-only tools (student profile, academic record, assessment results, skill scores, progress, department data, eligibility rules, company requirements); GET `/analytics/faculty`, `/analytics/hod`, `/analytics/placement`.
**Pages:** /assistant, /faculty, /hod, /placement.
**Rules:** citations required; insufficient-evidence fallback; every MCP tool has authN, authZ, validation, output schema and audit logging; no arbitrary SQL.

### Module 9: Admin Panel
**Endpoints:** GET/PUT `/admin/users`, GET `/admin/audit-logs`, GET/POST `/admin/faculty-assignments`.
**Pages:** /admin (departments, roles, skills, assessment config, users, permissions, knowledge sources, audit logs).

### Cross-cutting: Email & File Uploads
SMTP service abstraction (welcome, reset, assessment results); storage abstraction (local first, Azure Blob later).

---

## PHASE EXECUTION PLAN

Each product phase ends with a STOP and the Section 25 report (phase done, requirements, files created/modified, tests and results, APIs, DB changes, known issues, assumptions, security notes, docs updated, next phase). Inside a phase, agents run in parallel where independent.

| Phase | Scope | Agents |
|-------|-------|--------|
| 0 | Foundation: structure, config, DB, logging, errors, auth, RBAC, tenant scoping, health, Docker, test framework | DATABASE, BACKEND, FRONTEND, DEVOPS (parallel) |
| 1 | Student & Academic Profile | DATABASE → BACKEND ∥ FRONTEND |
| 2 | Skill Assessment | DATABASE → BACKEND ∥ FRONTEND |
| 3 | Readiness & Skill Gap Engine | DATABASE → BACKEND ∥ FRONTEND |
| 4 | Career Explorer & Roadmap | DATABASE → BACKEND ∥ FRONTEND |
| 5 | Student Dashboard + basic placement dashboard | BACKEND ∥ FRONTEND |
| 6 | Resume & Interview Intelligence | DATABASE → BACKEND ∥ FRONTEND |
| 7 | Job & Company Matching | DATABASE → BACKEND ∥ FRONTEND |
| 8 | RAG + MCP + advanced analytics | all agents; needs approval of LLM/vector decisions first |

**Per-phase quality step:** TEST-AGENT (pytest + RTL, 80%+ coverage on new code, including RBAC and tenant-isolation tests), REVIEW-AGENT (security and code quality audit).

**Note:** the repo has no TEST-AGENT or REVIEW-AGENT definition files; the ORCHESTRATOR should use general-purpose agents with `skills/TESTING.md` and a security checklist, or create those definitions first.

---

## VALIDATION GATES

| Gate | Commands |
|------|----------|
| Foundation | `pip install -r requirements.txt`, `alembic upgrade head`, `npm install`, `docker-compose config` |
| Per phase (lint/types) | `ruff check backend/`, `mypy backend/app`, `npm run lint`, `npm run type-check` |
| Per phase (tests) | `pytest --cov --cov-fail-under=80`, `npm test` |
| Final | `docker-compose build`, `docker-compose up -d`, `curl localhost:8000/health` |

---

## ENVIRONMENT VARIABLES

```env
DATABASE_URL=postgresql://user:password@localhost:5432/gradnexa
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=
UPLOAD_DIR=./uploads
MAX_UPLOAD_MB=10
LLM_PROVIDER=
LLM_API_KEY=
VITE_API_URL=http://localhost:8000
```

---

## OPEN QUESTIONS (resolve before the phase that needs them)

| Question | Needed by |
|----------|-----------|
| Faculty-to-student assignment model | Phase 1 |
| Default readiness weights and level thresholds | Phase 3 |
| Initial departments and skill frameworks, and who validates them | Phase 2-4 |
| Single college or multi-college from day one | Phase 0 |
| Resume parsing approach and LLM provider | Phase 6 |
| File storage target and retention period | Phase 6 |

---

## NEXT STEP

Execute with agents (starts with Phase 0 only, then stops for approval):
/execute-prp PRPs/gradnexa-prp.md
