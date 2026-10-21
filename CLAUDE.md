# CLAUDE.md - GradNexa Project Rules

> Project-specific rules for Claude Code. This file is read automatically.

---

## Project Overview

**Project Name:** GradNexa
**Description:** Engineering career intelligence platform: evidence-based assessment, explainable readiness scoring, skill-gap analysis and personalized plans for engineering graduates across all departments.
**Requirements source:** `requirement docs/AI_Engineering_Career_Intelligence_All_Departments_Master_Product_Development_Prompt.txt`
**Product definition:** `INITIAL.md`
**Tech Stack:**
- Backend: FastAPI + Python 3.11+
- Frontend: React + Vite + TypeScript
- Database: PostgreSQL + SQLAlchemy (pgvector later for RAG)
- Auth: Email/Password, JWT access + refresh, RBAC
- UI: Tailwind CSS + shadcn/ui

---

## Project Structure

```
GradNexa/
├── backend/
│   ├── app/
│   │   ├── main.py, config.py, database.py
│   │   ├── models/      (college, user, department, student, academic_record,
│   │   │                 skill, assessment, readiness, career_role, resume,
│   │   │                 learning_plan, company, audit_log)
│   │   ├── schemas/
│   │   ├── routers/
│   │   ├── services/    (readiness, skill_gap, eligibility, scoring, resume, plan)
│   │   └── auth/
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/, pages/, hooks/, services/, context/, types/
├── docs/                # REQUIREMENT_ANALYSIS.md, ARCHITECTURE.md, ...
├── requirement docs/
├── skills/
├── agents/
├── .claude/commands/
└── PRPs/
```

---

## Code Standards

### Python (Backend)
```python
# ALWAYS use type hints and docstrings on public functions
def get_student(db: Session, student_id: int, college_id: int) -> Student:
    """
    Fetch a student within the caller's college.

    Args:
        db: Database session
        student_id: Student primary key
        college_id: Tenant scope from the authenticated user

    Returns:
        Student object
    """
    pass

@router.get("/students/{id}")
async def read_student(id: int, db: Session = Depends(get_db)):
    pass
```

### TypeScript (Frontend)
```typescript
// ALWAYS define interfaces - NO any types
interface ReadinessScore {
  overall: number;
  categoryScores: Record<string, number>;
  ruleVersion: number;
}

const fetchReadiness = async (studentId: number): Promise<ReadinessScore> => { ... };
```

---

## Forbidden Patterns

### Backend
- ❌ `print()` - use `logging`
- ❌ Plain-text passwords - use bcrypt
- ❌ Hardcoded secrets - use environment variables
- ❌ `SELECT *` - specify columns
- ❌ Skipping input validation
- ❌ Queries not scoped by `college_id` (tenant isolation)

### Frontend
- ❌ `any` type
- ❌ `console.log` in production
- ❌ Skipping error handling in async operations
- ❌ Inline styles - use Tailwind / shadcn/ui

---

## Product Rules (from the master prompt, non-negotiable)

- **Configurable, never hard-coded:** departments, skills, career roles, role-skill mappings, readiness weights, eligibility rules. No `if department == "CSE"` logic.
- **Deterministic scoring:** readiness scores and assessment scores are computed by code. The LLM must never produce or alter a numeric score.
- **Eligibility is separate from readiness.** Never merge them into one score or one opaque value.
- **No placement predictions.** Never output "85% chance of placement". Use levels ("Strong", "Needs improvement") and statements like "meets configured eligibility criteria".
- **Explainable and versioned:** every score stores rule version and supporting evidence.
- **No fabrication:** no hard-coded student results, fake scores, fake citations, fake MCP responses, or invented resume facts. If a feature isn't built, say "Not implemented in this phase."
- **No invented policies.** Unknown business rules become open questions in `INITIAL.md` plus configurable settings; ask before implementing irreversible logic.
- **RAG answers cite sources;** with insufficient evidence reply: "I don't have enough approved information to answer this confidently."
- **MCP tools are read-only at first,** with authN, authZ, input validation, output schema and audit logging. The LLM never runs arbitrary DB queries.
- **Access control:** students see only their own data; faculty only assigned students; TPO/HOD only their college/department scope.

---

## Phased Delivery

Build incrementally. After each phase, report (phase done, requirements, files created/modified, tests and results, APIs, DB changes, known issues, assumptions, security notes, docs updated, next phase), then **STOP and wait for approval**.

| Phase | Module group |
|-------|--------------|
| 1 | Student & Academic Profile |
| 2 | Skill Assessment |
| 3 | Readiness & Skill Gap Engine |
| 4 | Career Explorer & Roadmap |
| 5 | Student Dashboard |
| 6 | Resume & Interview Intelligence |
| 7 | Job & Company Matching |
| 8 | RAG + MCP and advanced placement analytics |

MVP follows master prompt Section 30. Auth, college/departments and the basic placement dashboard ride along with the phases above. Every phase must be tested and documented.

---

## Module-Specific Rules

### Assessment
- Questions map to skills, difficulty, departments and roles; assessments are versioned.
- Scoring (including negative marking) is deterministic; keep full attempt history.

### Readiness
- Weights live in a versioned `ReadinessRule`; changing weights creates a new version.
- Show overall, category, department and role-specific scores, each with evidence.

### Skill Gap
- gap = max(required - current, 0); priority derived from configurable thresholds.

### Resume
- Every extracted fact links to its source text where practical.

### Learning Plan
- Built only from configured skills, approved learning resources and assessment evidence.

---

## API Conventions

- All endpoints prefixed with `/api/v1/`
- Plural nouns: `/students`, `/assessments`, `/career-roles`
- Status codes: 200 OK, 201 Created, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict

---

## Authentication

- Email/Password only (bcrypt hashing)
- Roles: STUDENT, FACULTY, TPO, HOD, ADMIN, SUPER_ADMIN
- Access token: 30 minutes; refresh token: 7 days; HS256
- Rate-limit auth endpoints; audit-log security-relevant events

---

## Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/gradnexa

# Auth
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=

# File storage
UPLOAD_DIR=./uploads
MAX_UPLOAD_MB=10

# LLM / RAG (post-MVP)
LLM_PROVIDER=
LLM_API_KEY=

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## Development Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Docker
docker-compose up -d

# Tests
docker compose -f docker-compose.test.yml up -d   # test PostgreSQL (once)
cd backend && pytest -v
cd frontend && npm test

# Linting
ruff check backend/
cd frontend && npm run lint && npm run type-check
```

---

## Commit Message Format

```
feat([module]): add [feature]
fix([module]): fix [bug]
refactor([module]): refactor [component]
test([module]): add tests for [feature]
docs: update [documentation]
```

---

## Skills Reference

| Task | Skill to Read |
|------|---------------|
| Database models | skills/DATABASE.md |
| API + Auth | skills/BACKEND.md |
| React + UI | skills/FRONTEND.md |
| Testing | skills/TESTING.md |
| Deployment | skills/DEPLOYMENT.md |

---

## Agent Coordination

For complex tasks, the ORCHESTRATOR coordinates:
- DATABASE-AGENT → models and migrations
- BACKEND-AGENT → API development
- FRONTEND-AGENT → UI components
- DEVOPS-AGENT → deployment

Read agent definitions in `/agents/`. (TEST-AGENT and REVIEW-AGENT are listed in `INITIAL.md` but have no definition file yet.)
