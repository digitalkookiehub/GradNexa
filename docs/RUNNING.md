# Running GradNexa

Setup: `cp .env.example .env` and replace the placeholders (at minimum `POSTGRES_PASSWORD` and `SECRET_KEY`).

## Backend (local)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Checks: `ruff check . && mypy app && pytest --cov=app --cov-fail-under=80`

## Frontend (local)

```bash
cd frontend
npm ci
npm run dev          # http://localhost:5173
```

Checks: `npm run lint && npm run type-check && npm test && npm run build`

## Docker (production-like)

```bash
docker compose up -d --build      # db -> migrations -> backend -> frontend
curl localhost/health            # via nginx; the backend itself is not published
docker compose logs -f backend
docker compose down               # add -v to delete the database volume
```

Frontend: http://localhost (nginx proxies `/api/` to the backend). Full production guide: docs/DEPLOYMENT.md.

## Docker (development, hot reload)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Backend reloads on changes in `backend/app`; Vite dev server runs at http://localhost:5173.
