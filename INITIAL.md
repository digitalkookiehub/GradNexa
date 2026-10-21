# INITIAL.md - GradNexa Product Definition

> GradNexa is an engineering career intelligence platform that takes engineering graduates from where they are now to industry-ready, using evidence-based assessment, explainable readiness scoring, skill-gap analysis and personalized plans.

Source requirements: `requirement docs/AI_Engineering_Career_Intelligence_All_Departments_Master_Product_Development_Prompt.txt` (the master prompt). Where this file and the master prompt disagree, the master prompt's rules (Sections 8, 9, 24-28) win.

---

## PRODUCT

### Name
GradNexa

### Tagline
From Engineering Graduate to Industry-Ready Professional.

### Description
A unified, multi-department platform for engineering colleges. For every student it answers four questions:
1. Where is the student now?
2. Which career roles align with their demonstrated skills and goals?
3. What skills are missing?
4. What should they do next?

It is NOT a generic AI chatbot. It provides evidence-based assessment, deterministic and explainable readiness scoring, department-specific skill-gap analysis, personalized learning plans, reassessment, and institutional placement intelligence.

### Target Users
- Primary: Students, Faculty/Mentors, Placement Officers (TPO), HODs, College Administrators
- Future: Trainers, Recruiters/Employers, Parents/Guardians

### Type
- [x] SaaS (multi-tenant: one tenant per college)

---

## TECH STACK

### Backend
- [x] FastAPI + Python 3.11+

### Frontend
- [x] React + Vite + TypeScript

### Database
- [x] PostgreSQL (+ pgvector for RAG in a later phase)

### Authentication
- [x] Email/Password (JWT access + refresh tokens), with RBAC
- [ ] Google OAuth (not selected)
- Note: the master prompt prefers an enterprise identity provider. Email/password is the chosen launch method; keep the auth layer swappable.

### UI Framework
- [x] Tailwind CSS + shadcn/ui

### Payments
- [ ] None at launch

### AI (post-MVP phases)
- LLM: configurable provider (Azure OpenAI or other); LLM never computes scores
- RAG: pgvector, lightweight custom pipeline unless LangChain/LangGraph is justified
- MCP: Python MCP / FastMCP, read-only first

---

## MODULES

> Delivery is phased. The 8 module groups below map to the product phases. Department, role, skill and rule data is **configuration in the database, never hard-coded**.

### Module 1: Authentication & Role Management (Required)

**Description:** Email/password auth, JWT sessions, RBAC, college (tenant) isolation.

**Roles:** STUDENT, FACULTY, TPO, HOD, ADMIN (college admin), SUPER_ADMIN

**Models:**
- College: id, name, code, is_active, created_at
- User: id, college_id, email, hashed_password, full_name, role, is_active, is_verified, created_at
- RefreshToken: id, user_id, token_hash, expires_at, revoked
- AuditLog: id, college_id, user_id, action, resource, resource_id, metadata, created_at

**API Endpoints:**
- POST /api/v1/auth/register, /login, /refresh, /logout
- POST /api/v1/auth/forgot-password, /reset-password
- GET/PUT /api/v1/auth/me

**Frontend Pages:** /login, /register, /forgot-password, /reset-password, /profile

---

### Module 2 (Phase 1): Student & Academic Profile

**Description:** Student identity, department, academic record, projects, certifications, career goals.

**Models:**
- Department: id, college_id, name, code, is_active
- Student: id, user_id, college_id, department_id, roll_number, graduation_year, phone, career_goal_role_ids
- AcademicRecord: id, student_id, semester, cgpa, active_arrears, attendance_pct
- Project: id, student_id, title, description, skills, url
- Certification: id, student_id, name, issuer, issued_on

**Actions:** Create/edit profile, select department, add academic info, add projects/certifications, select career goals.

**Pages:** /onboarding (profile → academics → department → career goals), /profile/academics, /profile/projects

---

### Module 3 (Phase 2): Skill Assessment

**Description:** Deterministic assessment engine with question bank, attempts, scoring and history.

**Models:**
- SkillCategory, Skill (configurable; common vs department-specific)
- Assessment: id, college_id, title, type, version, time_limit, max_attempts, negative_marking
- AssessmentQuestion: id, assessment_id, skill_id, difficulty, body, options, answer_key
- AssessmentAttempt, AssessmentResult: scores per skill and category
- StudentSkill: student_id, skill_id, score, confidence, evidence_ref

**Actions:** Admin/faculty author question bank and assessments; students attempt, view results and history. Scoring is deterministic.

**Pages:** /assessments, /assessments/{id}/attempt, /assessments/{id}/result, /assessments/history; admin: /admin/question-bank

---

### Module 4 (Phase 3): Readiness & Skill Gap Engine

**Description:** Deterministic, configurable, versioned readiness scoring and skill-gap analysis. Eligibility is kept strictly separate.

**Models:**
- ReadinessRule (versioned weights): category weights for aptitude, technical, communication, problem solving, resume, interview, projects, academics
- ReadinessScore: student_id, rule_version, overall, category_scores, role_id, evidence, computed_at
- SkillGap: student_id, role_id, skill_id, current, required, gap, priority, recommended_action

**Rules:**
- LLM must never produce the numeric score
- No placement-probability claims; use levels such as "Strong" or "Needs improvement"
- Every score shows its supporting evidence

**Pages:** /readiness, /readiness/gaps?role={id}

---

### Module 5 (Phase 4): Career Explorer & Roadmap

**Description:** Configurable career roles per department, role-skill mappings, personalized 30-day learning plan.

**Models:**
- CareerRole: id, college_id, department_id, name, description
- RoleSkill: role_id, skill_id, required_level, weight
- LearningResource: id, skill_id, title, url, approved_by
- LearningPlan, LearningPlanItem: week, skill_id, resource_id, status

**Actions:** Browse roles, select target roles, view role requirements, generate and track the plan (grounded in configured skills, approved resources and assessment evidence), reassess.

**Pages:** /careers, /careers/{id}, /plan, /plan/progress

---

### Module 6 (Phase 5): Student Dashboard

**Description:** Single view of readiness, skill scores, goals, gaps, plan, assessment history, resume score, progress.

**Pages:** /dashboard, /settings

---

### Module 7 (Phase 6): Resume & Interview Intelligence

**Description:** Resume upload and analysis with traceable extraction, role/JD comparison; text-based mock interviews.

**Models:**
- Resume: id, student_id, file_ref, uploaded_at
- ResumeAnalysis: resume_id, extracted (education, skills, projects, certifications, experience), missing_skills, role_match, source_spans
- MockInterview, InterviewResult: role_id, questions, answers, competency_scores

**Rules:** Never fabricate resume facts; every extracted fact traceable to source where practical. Avoid unsupported personality/psychological claims in interviews.

**Pages:** /resume, /resume/{id}/analysis, /interview, /interview/{id}/result

---

### Module 8 (Phase 7): Job & Company Matching

**Description:** Companies, job descriptions and deterministic eligibility rules, separate from readiness.

**Models:**
- Company, JobDescription
- EligibilityRule: cgpa_min, max_arrears, attendance_min, departments, graduation_year, custom criteria

**Pages:** /jobs, /jobs/{id} (eligibility result and skill requirements shown separately); admin: /admin/companies

---

### Module 9 (Phase 8): RAG + MCP and Advanced Placement Analytics

**Description:** Governed AI layer and institutional analytics.

- RAG: ingestion → parsing → chunking → metadata → embeddings (pgvector) → retrieval → citations. If evidence is insufficient: "I don't have enough approved information to answer this confidently."
- MCP: read-only tools (student profile, academic record, assessment results, skill scores, progress, department data, eligibility rules, company requirements), each with authN, authZ, input validation, output schema, audit logging.
- Orchestration: authenticate → MCP data → RAG evidence → deterministic calculation → LLM explanation → citations → audit.
- Models: RAGDocument, RAGChunk, MCPTool

**Pages:** /assistant (cited answers); dashboards below.

---

### Module 10: Admin Panel & Role Dashboards

**Description:** Admin configuration and college dashboards.

**API Endpoints:**
- CRUD /api/v1/admin/departments, /skills, /skill-categories, /roles, /readiness-rules
- GET/PUT /api/v1/admin/users
- GET /api/v1/admin/audit-logs
- GET /api/v1/analytics/faculty, /hod, /placement

**Frontend Pages:**
- /admin (departments, roles, skills, assessment config, users, permissions, knowledge sources, audit logs)
- /faculty (assigned students, gaps, students needing support)
- /hod (department readiness, skill heatmap, role distribution, trends)
- /placement (college-wide readiness, department comparison, role readiness, company eligibility, training priorities)

---

### Cross-cutting: Email Notifications & File Uploads

- Email: welcome, password reset, assessment results
- File uploads: resumes (PDF/DOCX), certificates; secure validation, size/type limits, storage behind an abstraction (local → Azure Blob or equivalent)

---

## MVP SCOPE

> Per master prompt Section 30. Build incrementally and stop for approval after each phase.

### Must Have (MVP)
- [x] Authentication and RBAC
- [x] College and departments (configurable)
- [x] Student and academic profile
- [x] Career role selection
- [x] Resume analysis
- [x] Assessments (deterministic scoring)
- [x] Deterministic readiness score
- [x] Skill-gap analysis
- [x] Personalized 30-day plan
- [x] Student dashboard
- [x] Basic placement officer dashboard

### Post-MVP (in order)
1. RAG
2. MCP
3. AI orchestration / career assistant
4. Mock interviews
5. Advanced analytics (faculty, HOD, full placement dashboards)

---

## ACCEPTANCE CRITERIA

### Authentication
- [ ] User can register and log in with email/password
- [ ] JWT access/refresh tokens work; protected routes redirect to login
- [ ] Students see only their own data; faculty only assigned students; TPO only their college
- [ ] Every request is scoped to the user's college (tenant isolation)

### Configuration
- [ ] Admin can create departments, skills, career roles and role-skill mappings without code changes
- [ ] No department-specific logic is hard-coded

### Assessment & Readiness
- [ ] Assessment scoring is deterministic and reproducible
- [ ] Readiness score uses configurable, versioned weights and shows evidence per category
- [ ] LLM never calculates a numeric score
- [ ] No placement-probability language anywhere in the product
- [ ] Eligibility results are never merged into the readiness score

### Skill Gap & Plan
- [ ] Gap = required level minus current level per role skill, with priority and recommended action
- [ ] 30-day plan is built only from configured skills and approved resources

### Resume
- [ ] Extraction never fabricates facts; extracted items link to source text

### Quality
- [ ] All API endpoints documented in OpenAPI
- [ ] Backend test coverage 80%+
- [ ] Frontend TypeScript strict mode passes
- [ ] Docker builds and runs successfully

---

## SPECIAL REQUIREMENTS

### Security
- [x] RBAC with tenant/college isolation
- [x] Rate limiting on auth endpoints
- [x] Input validation on all endpoints
- [x] Secure file upload (type, size, content checks)
- [x] Audit logging; PII protection; data retention policy
- [x] SQL injection and XSS prevention
- [x] Secrets only via environment variables

### Integrations
- [x] Email service for notifications
- [x] File storage service (resumes, certificates)
- [ ] Payments (none)
- [ ] LLM provider and embeddings (post-MVP)

### Business-Rule Discipline
Never invent institutional policies. Unknown rules (readiness weights, pass thresholds, eligibility criteria, skill frameworks per department) become open questions and configurable settings.

---

## OPEN QUESTIONS

- Default readiness weights and level thresholds (Strong / Moderate / Needs improvement)?
- Initial departments and skill frameworks to seed, and who validates them?
- Faculty-to-student assignment model (by section, batch or manual)?
- Resume parsing approach and LLM provider for extraction?
- File storage target and data retention period?
- Single college or multi-college from day one?

---

## AGENTS

| Agent | Role | Works On |
|-------|------|----------|
| DATABASE-AGENT | Models and migrations | All database models |
| BACKEND-AGENT | API endpoints and services | All modules' backends |
| FRONTEND-AGENT | UI pages and components | All modules' frontends |
| DEVOPS-AGENT | Docker, CI/CD, environments | Infrastructure |
| TEST-AGENT | Unit and integration tests | All code |
| REVIEW-AGENT | Security and code quality audit | All code |

---

# READY?

```bash
/generate-prp INITIAL.md
```

Then:

```bash
/execute-prp PRPs/gradnexa-prp.md
```
