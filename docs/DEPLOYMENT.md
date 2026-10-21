# Deploying GradNexa

Stack: `db` (Postgres 16 + pgvector) -> `backend` (FastAPI, Uvicorn workers, runs migrations on start) -> `frontend` (nginx: serves the SPA and proxies `/api/`). Only the frontend port is published.

## First deployment

```bash
cp .env.example .env
# Edit .env. Required:
#   POSTGRES_PASSWORD   a strong random value
#   SECRET_KEY          python -c "import secrets; print(secrets.token_urlsafe(48))"
# Optional: FRONTEND_PORT, WEB_CONCURRENCY (default 2), BCRYPT_ROUNDS (default 12), SMTP_*.
docker compose up -d --build
docker compose ps                      # backend must become "healthy"
```

The backend refuses to start in production mode (`ENVIRONMENT=production`, set by compose) when `SECRET_KEY` is short or a placeholder, rate limiting is off, `BCRYPT_ROUNDS` < 10 or CORS contains `*`. API docs (`/docs`, `/openapi.json`) are disabled in production.

### Create the first college and admin

```bash
docker compose exec -e ADMIN_PASSWORD='<strong password>' backend \
  python -m scripts.seed_college --name "Your College" --code YC \
  --admin-email admin@yourcollege.edu --admin-full-name "Admin" \
  --departments "Computer Science:CSE,Mechanical:MECH"
```
The password is read only from the environment and never logged. Departments, skills, readiness rules and everything else are then configured by the admin in the app (nothing is hard-coded).

### Optional: load a starter configuration

To avoid starting from an empty college, load the generic engineering starter set (skills, roles, a readiness rule, 4 assessments with 33 questions, approved learning resources, interview questions, and a draft sample job). With the API running:

```bash
cd backend
ADMIN_PASSWORD='<the admin password>' python -m scripts.load_starter_pack --email admin@yourcollege.edu
```
It goes through the admin API (so it is validated and audit-logged), is safe to re-run, and never publishes the sample job. **Every number in it is a placeholder for the college to review**: weights, level cut-offs, gap thresholds, required levels, questions and resource links are not the college's policy. Edit them in the app, or pass your own file with `--pack`.

## HTTPS

nginx in this stack speaks HTTP only. Terminate TLS in front of it (a cloud load balancer, Caddy, Traefik or a host nginx) and add `Strict-Transport-Security` there. nginx sets `X-Forwarded-For` to the address it sees, so if another proxy sits in front, forward the real client IP (set the proxy to pass `X-Forwarded-For` and change `nginx-snippets/proxy.conf` to `$proxy_add_x_forwarded_for`) or rate limiting will count every user as one client.

## Updating

```bash
git pull
docker compose up -d --build           # migrations run automatically before the new backend serves traffic
```
Take a backup first (below). Migrations are forward-only in production; to roll back, restore the backup taken before the update and deploy the previous image.

## Backups and restore

```bash
scripts/backup_db.sh backups                         # compressed pg_dump (custom format)
docker compose stop backend frontend
CONFIRM=yes scripts/restore_db.sh backups/gradnexa-<timestamp>.dump
docker compose up -d
```
- The restore script replaces the whole database and refuses to run without `CONFIRM=yes`.
- Uploaded files (resumes, knowledge documents) live in the `uploads_data` Docker volume and are **not** in the database dump. Back that volume up too (for example `docker run --rm -v <project>_uploads_data:/data -v "$PWD/backups":/out alpine tar czf /out/uploads.tgz -C /data .`).
- Schedule the backup (cron / Task Scheduler), copy dumps off the machine, and test a restore periodically. Retention is not defined yet (open question).
- A backup/restore round trip was verified on the compose stack: a document was created, backed up, deleted, and was present again after restore.

## Operations

- Logs: `docker compose logs -f backend` (JSON lines). Liveness `/health`, readiness (checks the database) `/health/ready`.
- Scale: raise `WEB_CONCURRENCY` or run more backend replicas behind the proxy. Endpoints use synchronous DB sessions, so more workers means more throughput.
- Secrets live only in `.env` / the host environment. Rotating `SECRET_KEY` signs every user out.
- Not provided: metrics/alerting, centralised log shipping, automatic TLS. Choose these with your hosting provider.

## Development stack

`docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build` (hot reload, backend on :8000, frontend on :5173, rate limiting off, fast hashing).

## Dependencies and security audits

- `backend/requirements.txt` pins exact versions. On 2026-10-18 `pip-audit` flagged FastAPI/Starlette 0.38, PyJWT 2.10, python-multipart 0.0.12, pypdf 6.9 and pytest 8.3; they were upgraded to the pinned versions (FastAPI 0.143.5, Starlette 1.8.0, PyJWT 2.15.1, python-multipart 0.0.32, pypdf 6.21.1, pytest 9.1.1) and the full suite plus a production-stack smoke test were re-run. `pip-audit` then reported no known vulnerabilities.
- CI runs `pip-audit` (fails on any finding) and `npm audit --omit=dev --audit-level=high`. Two *moderate* advisories remain in `react-router-dom` (frontend); they do not fail CI.
- Existing local environments need `pip install -r backend/requirements.txt` to pick up the upgrade.
- The route-security sweep reads routes from the OpenAPI schema because FastAPI >= 0.14x no longer exposes plain route objects on `app.routes`.
