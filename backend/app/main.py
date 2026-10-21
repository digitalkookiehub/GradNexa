"""FastAPI application entrypoint."""
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.dependencies import limiter
from app.exceptions import register_exception_handlers
from app.logging_config import configure_logging
from app.routers import (
    admin,
    admin_assessments,
    admin_companies,
    admin_hod_assignments,
    admin_interview_questions,
    admin_jobs,
    admin_knowledge,
    admin_learning_resources,
    admin_mcp,
    admin_readiness,
    admin_users,
    assessments,
    assistant,
    auth,
    departments,
    faculty_dashboard,
    guide,
    health,
    hod_dashboard,
    interviews,
    jobs,
    knowledge,
    mcp,
    placement_analytics,
    placement_dashboard,
    planning,
    readiness,
    resumes,
    skills,
    student_dashboard,
    students,
)

configure_logging(settings.LOG_LEVEL)

IS_PRODUCTION = settings.ENVIRONMENT.lower() == "production"

# Interactive API docs and the schema are development tools; they are not served in production.
app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


@app.middleware("http")
async def add_security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Attach baseline security headers to every API response."""
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return 429 with the standard error body."""
    return JSONResponse({"detail": "Too many requests"}, status_code=429)


app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(departments.router, prefix="/api/v1")
app.include_router(students.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(admin_assessments.router, prefix="/api/v1")
app.include_router(assessments.router, prefix="/api/v1")
app.include_router(skills.router, prefix="/api/v1")
app.include_router(admin_readiness.router, prefix="/api/v1")
app.include_router(readiness.router, prefix="/api/v1")
app.include_router(admin_learning_resources.router, prefix="/api/v1")
app.include_router(planning.router, prefix="/api/v1")
app.include_router(student_dashboard.router, prefix="/api/v1")
app.include_router(placement_dashboard.router, prefix="/api/v1")
app.include_router(interviews.router, prefix="/api/v1")
app.include_router(admin_interview_questions.router, prefix="/api/v1")
app.include_router(resumes.router, prefix="/api/v1")
app.include_router(admin_companies.router, prefix="/api/v1")
app.include_router(admin_jobs.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(admin_knowledge.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(admin_hod_assignments.router, prefix="/api/v1")
app.include_router(faculty_dashboard.router, prefix="/api/v1")
app.include_router(hod_dashboard.router, prefix="/api/v1")
app.include_router(placement_analytics.router, prefix="/api/v1")
app.include_router(mcp.router, prefix="/api/v1")
app.include_router(admin_mcp.router, prefix="/api/v1")
app.include_router(assistant.router, prefix="/api/v1")
app.include_router(guide.router, prefix="/api/v1")
app.include_router(admin_users.router, prefix="/api/v1")
