# Phase 16 - Testing and Security Hardening

## Added
- `BCRYPT_ROUNDS` setting (default 12; tests use 4). Full backend suite: ~16-23 min -> ~1 min. (The suite later moved to PostgreSQL only with rollback-per-test isolation; it still takes about 1 minute.)
- Production config guard (`ENVIRONMENT=production`): the app refuses to start if SECRET_KEY is < 32 chars or a placeholder, rate limiting is off, BCRYPT_ROUNDS < 10, or CORS contains `*`.
- Security headers on every API response: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Cache-Control: no-store`.
- `tests/test_security_sweep.py`: generated from the live route table. Every non-public `/api/v1` route must return 401 without a token; a malformed token never passes; every `/admin` route returns 403 for a student. New endpoints added without auth fail this test.
- `tests/test_hardening.py`: forged-key, `alg=none`, expired and unknown-user tokens rejected; role claims inside a token cannot escalate; tenant claim cannot switch college; production config guard cases.

## Load check (live server, Postgres, 10 concurrent clients, 60 requests per endpoint)
| Endpoint | p50 | p95 | req/s |
|---|---|---|---|
| GET /students/me | 63 ms | 76 ms | 157 |
| POST /knowledge/search | 99 ms | 110 ms | 99 |
| POST /assistant/query | 117 ms | 128 ms | 85 |
| GET /dashboard/student | 177 ms | 210 ms | 55 |
| GET /mcp/tools | 198 ms | 223 ms | 50 |

Small single-machine check, not a capacity plan. On Windows use `127.0.0.1`, not `localhost` (IPv6 fallback adds ~2 s per request).

## Known limits
- Endpoints are `async def` with synchronous DB sessions, so DB work blocks the event loop; throughput is bounded by one worker's serial DB time. Run several Uvicorn workers in deployment or move to `def` endpoints.
- No dependency vulnerability scan, no HTTPS/HSTS (belongs to the proxy in Phase 17), no per-account lockout beyond IP rate limits.
