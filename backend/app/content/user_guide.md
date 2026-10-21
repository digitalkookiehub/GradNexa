# GradNexa User Guide

**GradNexa: From Engineering Graduate to Industry-Ready Professional.**

This guide explains what the application does, who uses it, and the order in which things happen. Part 1 is for everyone. Parts 2 to 6 are per role. Part 7 explains how to read the numbers. Part 8 covers help and known limits.

---

## Part 1 - The big picture

### What GradNexa is

GradNexa helps an engineering student see, with evidence, how ready they are for a career role, what is missing, and what to do about it in the next 30 days. It also gives the college a view of where its students stand.

### What it deliberately does *not* do

- **It never predicts placement.** You will not see "85% chance of placement". You see levels such as *Strong* or *Needs improvement*, and statements such as "meets the configured eligibility criteria".
- **Every score is calculated by fixed rules, not by an AI model.** Each score shows the rule version and the evidence behind it. The assistant in this version does not use a language model.
- **Readiness and eligibility are two separate things.** Readiness = "how prepared am I for this role?". Eligibility = "do I meet this company's stated requirements (CGPA, arrears, attendance, department)?". They are never merged into one number.
- **Nothing is hard-coded.** Departments, skills, career roles, role-to-skill requirements, readiness weights and eligibility rules are all set up by your college.

### Who uses it

| Role | What they do | Where they land after login |
|---|---|---|
| **Student** | Builds a profile, takes assessments, sees readiness and skill gaps, follows a 30-day plan, practises interviews, analyses a resume, checks jobs | Dashboard |
| **Faculty** | Sees their assigned students; writes assessments, questions, learning resources, interview questions; manages knowledge documents | Faculty dashboard |
| **TPO** (training & placement officer) | Placement dashboard; manages companies and job postings | Placement dashboard |
| **HOD** (head of department) | Aggregate view of the departments assigned to them (no individual student records) | HOD dashboard |
| **Admin** | Configures everything for the college and can use all staff tools | Profile (use the top menu) |

### How the whole system fits together

```
 ADMIN CONFIGURES THE COLLEGE (once, then keeps improving it)
 ┌──────────────────────────────────────────────────────────────────────┐
 │ Departments → Skills → Career roles (+ required skill levels)        │
 │ → Readiness rule (weights & thresholds) → Assessments & questions    │
 │ → Learning resources → Interview questions → Companies & jobs        │
 └──────────────────────────────────────────────────────────────────────┘
                                   │
 STUDENT JOURNEY                   ▼
 Register → Onboarding → Academic records → Projects/certifications
      → Take assessments  ──►  skill scores (with evidence)
      → Readiness for a role ──► skill gaps (High / Medium / Low)
      → 30-day plan (built from the gaps + approved resources)
      → Mock interviews, resume analysis, job eligibility & skill fit
      → Dashboard summarises all of it; Assistant answers questions
                                   │
 STAFF VIEWS                       ▼
 Faculty: assigned students · HOD: department aggregates ·
 TPO/Admin: placement dashboard & analytics
```

The most important thing to know: **a student only sees useful results after the admin has finished the set-up chain.** If a student sees "Not enough evidence yet" or an empty list, it usually means something upstream has not been configured or attempted yet (see Part 8).

---

## Part 2 - Getting started

### Create the college (operator, one time)

The first college and its admin account are created by whoever installs the system:

```bash
ADMIN_PASSWORD='<strong password>' python -m scripts.seed_college \
  --name "Your College" --code YC \
  --admin-email admin@yourcollege.edu --admin-full-name "Admin" \
  --departments "Computer Science:CSE,Mechanical:MECH"
```
(In Docker: `docker compose exec -e ADMIN_PASSWORD=... backend python -m scripts.seed_college ...`. See `docs/DEPLOYMENT.md`.) The **college code** (`YC` above) is what students type when they register.

### Sign in and register

| Page | What to do |
|---|---|
| **Register** (`/register`) | Enter full name, email, a password of at least 8 characters, and your **college code**. Everyone who registers becomes a **Student**. |
| **Login** (`/login`) | Email and password. |
| **Forgot password** (`/forgot-password`) | Enter your email; if email sending is configured you receive a reset link, which opens **Reset password** (`/reset-password`). |
| **Log out** | Top-right button. Sessions use short-lived tokens that refresh automatically; after 7 days you must log in again. |

Too many login attempts in a minute are blocked temporarily ("Too many requests"). Wait a minute and retry.

### Staff accounts (important current limitation)

Registration always creates a Student. There is **no screen yet** for an admin to create or promote Faculty, TPO or HOD users or to list users. Until that is added, an operator must promote an account after the person registers normally:

```sql
-- run against the gradnexa database; replace the email and role
UPDATE users SET role = 'FACULTY' WHERE email = 'teacher@yourcollege.edu';
-- roles: STUDENT, FACULTY, TPO, HOD, ADMIN
```
Likewise, assigning faculty to students (`/api/v1/admin/faculty-assignments`) and creating departments after the first set (`/api/v1/admin/departments`) are available only through the API for now, not as screens. Assigning a HOD to departments has a screen (see Part 5) but asks for the HOD's numeric user id.

---

## Part 3 - Admin guide: set the college up

Do these **in this order**. Each step feeds the next. Admin menu items are shown in bold.

1. **Departments.** Created at install (seed) or via the API. Students pick their department in onboarding.
2. **Skills** (menu: *Skills*). Create skill categories (for example *Programming*, *Core engineering*, *Communication*) and the skills in them. Skills are the common language used by assessments, roles, resources, resumes and jobs, so keep names consistent.
3. **Career roles** (menu: *Career roles*). Create each role (for example *Backend Developer*, *Embedded Engineer*) and set the **required level for each skill** on that role. This is what "gap" is measured against.
4. **Readiness rules** (menu: *Readiness rules*). Define the category **weights** and the **level thresholds** (what score counts as *Strong*, *Needs improvement*, and so on) and the **gap thresholds** (when a gap is High / Medium / Low). **There are no default weights**, so a rule must exist and be activated before any readiness can be computed. Editing a rule creates a **new version**; old results keep the version they used, so history is never rewritten. *These numbers are institutional policy: agree them with your placement and academic leads.*
5. **Question bank and assessments** (menu: *Question bank*, *Assessments*). Write questions, each tied to a skill and a difficulty. Build an **assessment** from questions and set its time limit, maximum attempts and negative marking. Assessments are **versioned**: use *new version* instead of editing a published one. **Publish** to make it visible to students; *Archive* retires it.
6. **Learning resources** (menu: *Learning resources*). Add courses, articles and practice links against skills. A resource must be **approved** before it can appear in a student's plan. Plans are built only from approved resources.
7. **Interview questions** (menu: *Interview questions*). Add questions with a scoring **rubric** (the keywords/criteria used to score answers).
8. **Companies and jobs** (menu: *Companies*, *Jobs*). Add companies; add job postings (title, description, deadline, linked career role, required skills). Set **eligibility rules** on a job (minimum CGPA and which CGPA scale it uses, maximum arrears, minimum attendance, allowed departments). A job is hidden from students until you **Publish** it; *Close* ends it. Deadlines are dates (no time of day).
9. **Knowledge base** (menu: *Knowledge base*). Upload placement guides, interview guides, policies (PDF, DOCX, TXT or MD). A document is **Pending** until an admin **Approves** it; only approved documents are searched or cited by students and the assistant. You can archive or delete documents.
10. **HOD assignments** (menu: *HOD assignments*). Link a HOD user to one or more departments so the HOD dashboard shows those departments.
11. **MCP tools** (menu: *MCP tools*). Switch individual read-only assistant data tools on or off for your college.

**Good practice:** after step 7, log in as a test student and walk the student journey (Part 4) to confirm the numbers look sensible before announcing the system.

---

## Part 4 - Student guide

### Step 1 - Onboarding and profile

First login opens a short **Complete your profile** wizard: personal details (including **graduation year** and **department**), then your **semester records**, then a summary to confirm. You can edit later:

- **Profile** - personal details.
- **Academics** (`/profile/academics`) - for each semester: CGPA/SGPA, active arrears, attendance. These feed job eligibility. **Keep them accurate**: eligibility results depend on them. If a value is missing, eligibility shows *Unknown*, never a guess.
- **Projects & Certifications** (`/profile/projects`) - add projects and certificates (you can delete entries).

### Step 2 - Take assessments

**Assessments** lists the tests published for you. Open one, read its time limit, attempts allowed and whether wrong answers lose marks, then **Start**.

- Answers are saved as you go. **Submit** to finish; if time runs out the attempt is finalised for you.
- If you reach the maximum attempts you will see **Attempt limit reached**.
- The **result** page shows your score and the skills it measured. **History** lists all your past attempts; every attempt is kept.
- Each assessment result updates your **skill scores**. Skill scores are the evidence everything else is built on.

### Step 3 - See your readiness

**Readiness** (`/readiness`): pick a **career role**. You see:

- **General readiness** (overall) and **readiness for the chosen role**, shown as a level plus score;
- a **category breakdown** and the **skill scores** it came from (the evidence);
- the **rule version** used.

If there is too little evidence you will see **Not enough evidence yet**. That is an honest answer, not an error: take more assessments covering that role's skills.

### Step 4 - Understand your skill gaps

**Skill gaps** (`/readiness/gaps`): for the chosen role, each skill shows required level, your current level, the **gap** (never below zero) and its **priority** (High / Medium / Low, from your college's thresholds). If it says *Compute your readiness for this role first*, open Readiness for that role first.

### Step 5 - Explore careers

**Careers** lets you search roles and open a role to see the skills it needs and a roadmap. Use it to decide which role to target before checking readiness.

### Step 6 - Follow your 30-day plan

**Plan** (`/plan`) turns your High and Medium gaps into a four-week plan using your college's **approved learning resources**. Click **Generate a plan** (it needs your readiness for the role first). Tick items off as you finish them. Generating a new plan asks you to confirm first because it replaces the current one. **Plan history** (`/plan/progress`) shows earlier plans and progress. If a skill has no approved resource yet, the plan cannot invent one; tell your faculty/admin.

### Step 7 - Practise interviews

**Interview** (`/interview`): choose a role and how many questions (1 to 10), then **Start an interview**. Type your answers; **Finish** to get a score. Scoring is rubric-based (does your answer cover the expected points?), shown per question with the rubric, plus a plain disclaimer that it is practice feedback, not a prediction. **Your interviews** lists past sessions and results.

### Step 8 - Analyse your resume

**Resume** (`/resume`): upload a PDF or DOCX (up to 10 MB). GradNexa extracts text, finds sections and your college's configured skills, and links each finding back to the **source text** in your resume so you can see exactly where it came from. Optionally choose a **target role** or compare with a **job posting** (or paste a job description) to see *Found in resume* versus *Missing from resume*. It does not invent anything that is not in your document. You can delete a resume you uploaded.

### Step 9 - Check jobs

**Jobs** lists open postings. Filters let you search and filter by eligibility. On a job:

- **Eligibility** (separate from readiness): for each criterion (CGPA, arrears, attendance, department) you see **Met**, **Not met** or **Unknown** with the numbers compared. *Unknown* means your records are missing, not that you failed.
- **Skill fit**: how your skill scores line up with the job's required skills.
- A passed deadline is shown as such.

### Step 10 - Dashboard and Assistant

- **Dashboard** brings it together: readiness, top skill gaps, learning plan, and shortcuts to *Take an assessment*, *Skill gaps*, *Explore careers*, *My plan*, *Projects & certifications*. Parts without evidence say so.
- **Assistant** (`/assistant`): ask a question in plain language, optionally tied to a **career role** or **job**. It answers from **your own stored results** and from **approved college documents**, with **citations** for anything it quotes, and keeps *readiness* and *eligibility* in separate sections. If approved documents do not cover your question it replies exactly: *"I don't have enough approved information to answer this confidently."* It cannot see other students' data and ignores instructions inside your question that try to change that. In this version it does not use a language model.
- **Knowledge** (`/knowledge`): search the approved documents directly and see the passages with their source.

---

## Part 5 - Staff guides

### Faculty

- **Faculty dashboard** (`/faculty`): the students assigned to you, with readiness level, assessment activity and a **needs support** flag (a rule-based heuristic, not a prediction; sortable in the table) with the reasons (no readiness score, not enough evidence, or at least one High-priority skill gap). You see only assigned students.
- **Authoring**: *Assessments*, *Question bank*, *Learning resources*, *Interview questions*, *Knowledge base*. Use these as described in Part 3, steps 5 to 7 and 9. (Skills, career roles and readiness rules are Admin-only.)

### TPO (placement officer)

- **Placement dashboard** (`/placement`): college-wide placement readiness picture and analytics (role readiness, company eligibility counts, progress trends), always as levels and counts, never placement probabilities.
- **Companies** and **Jobs**: create companies and postings, set eligibility rules, publish and close (Part 3, step 8).
- **Knowledge search** for reference.

### HOD (head of department)

- **HOD dashboard** (`/hod`): **aggregates only** (counts, averages, distributions) for the departments an admin has assigned to you. You do not see individual student records. If the dashboard is empty, ask the admin to assign your departments.

### Admin

Everything in Part 3, plus the Placement dashboard, Faculty-style tools and Knowledge search.

---

## Part 6 - Typical end-to-end scenarios

**A. A new student, first week**
1. Register with the college code → complete onboarding (department, graduation year, semester records).
2. Take the published assessments for your target skills.
3. Open Readiness, pick a role → read Skill gaps.
4. Generate the 30-day plan and start the first week's items.
5. Do a mock interview and upload your resume; compare it with a job posting.
6. Check Jobs for eligibility; fix any *Unknown* by completing your Academics.

**B. Admin preparing a new batch**
1. Review skills and career roles; confirm an active readiness rule exists.
2. Publish assessments and approve learning resources for the weak skills.
3. Open and publish job postings with eligibility rules.
4. Upload and approve knowledge documents (guides, policies).
5. Assign HODs to departments; ask the operator to assign faculty to students.
6. Check the Placement dashboard after students start attempting assessments.

**C. Faculty checking on students**
1. Open the Faculty dashboard → check the **Needing support** count and sort the student table by the *needs support* column.
2. Read the reasons; add or approve a learning resource or a new assessment for the gap.

---

## Part 7 - How to read the numbers

| You see | It means |
|---|---|
| **Skill score** | Your result on assessment questions for that skill, calculated with the assessment's scoring rules (including negative marking if set). |
| **Readiness (overall / role)** | A weighted combination of skill scores using your college's active readiness rule. Shown with the **rule version** so it can always be explained. |
| **Level** (for example Strong / Needs improvement) | The band your score falls into according to the college's thresholds. |
| **Not enough evidence yet** | Too few relevant assessment results to give a trustworthy score. Take more assessments. |
| **Gap** | `max(required level - your level, 0)`. |
| **Priority** High / Medium / Low | Derived from the college's gap thresholds. |
| **Eligibility** Met / Not met / Unknown | A comparison of your academic records with a job's stated rules. Unknown = missing data. |
| **Skill fit** | How your skills match a job's required skills. Not the same as eligibility. |
| **Citation** | The approved document and passage an assistant answer or search result came from. |

Scores can change when your college publishes a new rule version or assessment version; older results remain tied to the version they used.

---

## Part 8 - Help, troubleshooting and limits

### Common situations

| Problem | Likely cause and fix |
|---|---|
| "Not enough evidence yet" | No (or too few) assessment results for the role's skills. Take assessments. |
| Readiness impossible for any role | Admin has not created or activated a readiness rule, or the role has no required skills. |
| Skill gaps says "Compute your readiness for this role first" | Open Readiness and select that role first. |
| Plan cannot be generated or is thin | Needs readiness for the role, and approved learning resources for the gap skills. |
| Eligibility shows *Unknown* | Academic records or attendance are missing; complete Academics. |
| No assessments or jobs listed | Nothing published yet for you (admin must publish; jobs must be OPEN). |
| Assistant says it lacks information | No approved document covers it. Ask an admin to upload and approve one. |
| "Attempt limit reached" | The assessment's maximum attempts used; ask faculty/admin if you need another. |
| "Too many requests" | Too many login attempts; wait a minute. |
| Staff user sees no menu items | Their account is still a Student role or has no assignments. See Part 2. |
| Resume upload rejected | Wrong file type or bigger than 10 MB. |

### What is not in this version

- No language-model answers and no AI-written feedback; the assistant is rule-based and cites approved documents.
- No semantic (embedding) search; knowledge search is keyword-based.
- No OCR for scanned PDFs (resumes and documents need selectable text).
- No admin screen for creating/promoting staff users, listing users, creating departments after setup, or assigning faculty to students (API or database only; see Part 2).
- No email notifications beyond password reset (when email is configured).
- No payments.
- A real-browser walkthrough of every screen has not yet been done; report anything that looks wrong.

### Privacy and access in one paragraph

Students see only their own data. Faculty see only assigned students. HODs see only aggregates for their departments. TPO and Admin see their own college only, and no one can see another college's data. Security-relevant actions (logins, publishing, approvals, uploads) are recorded in an audit log.

### Trying it locally

See `docs/RUNNING.md`. Frontend `http://localhost:5173`, backend `http://127.0.0.1:8000`. Production setup: `docs/DEPLOYMENT.md`.
