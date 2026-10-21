"""Load a starter configuration pack into a college through the admin HTTP API.

Usage (from backend/, API running):
    ADMIN_PASSWORD=... python -m scripts.load_starter_pack \
        --email admin@college.edu [--base-url http://127.0.0.1:8000] \
        [--pack scripts/starter_packs/engineering_starter.json]

Everything goes through the same endpoints the admin screens use, so each item gets the app's
own validation and audit logging. The script is idempotent: items that already exist (matched by
name or title) are left alone, so it is safe to re-run. The password is read only from the
ADMIN_PASSWORD environment variable and is never logged.

Departments are NOT created here (use scripts.seed_college). The sample job is left as a DRAFT so
students never see placeholder postings.
"""
import argparse
import json
import logging
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger("scripts.load_starter_pack")
DEFAULT_PACK = Path(__file__).parent / "starter_packs" / "engineering_starter.json"
Json = Any


class ApiError(RuntimeError):
    """An API call failed."""


class Client:
    """Tiny JSON client for the admin API."""

    def __init__(self, base_url: str) -> None:
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("--base-url must start with http:// or https://")
        self.base = base_url.rstrip("/") + "/api/v1"
        self.token: str | None = None

    def call(self, method: str, path: str, body: Json = None) -> Json:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(  # noqa: S310 - scheme checked in __init__
            self.base + path, data=data, method=method, headers=headers
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
                raw = resp.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:300]
            raise ApiError(f"{method} {path} -> {exc.code}: {detail}") from exc

    def login(self, email: str, password: str) -> None:
        out = self.call("POST", "/auth/login", {"email": email, "password": password})
        self.token = out["access_token"]


def load(client: Client, pack: Json) -> dict[str, int]:
    """Create everything in the pack that is missing; return how many items were created."""
    made: dict[str, int] = {}

    def count(kind: str) -> None:
        made[kind] = made.get(kind, 0) + 1

    departments = {d["code"]: d["id"] for d in client.call("GET", "/departments")}

    categories = {c["name"]: c["id"] for c in client.call("GET", "/skill-categories")}
    for cat in pack["categories"]:
        if cat["name"] not in categories:
            body: Json = {"name": cat["name"], "scope": cat["scope"], "department_id": None}
            if cat["scope"] == "DEPARTMENT":
                body["department_id"] = departments[cat["department"]]
            categories[cat["name"]] = client.call("POST", "/admin/skill-categories", body)["id"]
            count("skill categories")

    skills = {s["name"]: s["id"] for s in client.call("GET", "/skills")}
    for cat in pack["categories"]:
        for name in cat["skills"]:
            if name not in skills:
                skills[name] = client.call(
                    "POST", "/admin/skills", {"category_id": categories[cat["name"]], "name": name}
                )["id"]
                count("skills")

    roles = {r["name"]: r["id"] for r in client.call("GET", "/admin/career-roles")}
    for role in pack["roles"]:
        if role["name"] in roles:
            continue
        rid = client.call(
            "POST",
            "/admin/career-roles",
            {
                "name": role["name"],
                "description": role["description"],
                "department_id": None,
                "is_active": True,
            },
        )["id"]
        client.call(
            "PUT",
            f"/admin/career-roles/{rid}/skills",
            [
                {"skill_id": skills[s], "required_level": lvl, "weight": w}
                for s, lvl, w in role["skills"]
            ],
        )
        roles[role["name"]] = rid
        count("career roles")

    if not any(r["is_active"] for r in client.call("GET", "/admin/readiness-rules")):
        rule = pack["readiness_rule"]
        created = client.call(
            "POST",
            "/admin/readiness-rules",
            {
                "weights": {str(categories[name]): w for name, w in rule["weights"].items()},
                "level_thresholds": [{"level": n, "min_score": s} for n, s in rule["levels"]],
                "gap_thresholds": {
                    "high_min_gap": rule["high_min_gap"],
                    "medium_min_gap": rule["medium_min_gap"],
                },
            },
        )
        client.call("POST", f"/admin/readiness-rules/{created['id']}/activate")
        count("readiness rule")

    existing = {a["title"] for a in client.call("GET", "/admin/assessments")}
    for a in pack["assessments"]:
        if a["title"] in existing:
            continue
        aid = client.call(
            "POST",
            "/admin/assessments",
            {
                "title": a["title"],
                "type": a["type"],
                "department_id": None,
                "time_limit_min": a["time_limit_min"],
                "max_attempts": a["max_attempts"],
                "negative_marking": a["negative_marking"],
            },
        )["id"]
        for i, q in enumerate(a["questions"], start=1):
            client.call(
                "POST",
                f"/admin/assessments/{aid}/questions",
                {
                    "skill_id": skills[q["skill"]],
                    "difficulty": q["difficulty"],
                    "body": q["body"],
                    "options": q["options"],
                    "correct_option_ids": q["correct"],
                    "marks": q["marks"],
                    "position": i,
                },
            )
        client.call("POST", f"/admin/assessments/{aid}/publish")
        count("assessments (published)")

    have = {(r["skill_id"], r["title"]) for r in client.call("GET", "/admin/learning-resources")}
    for skill, title, url in pack["resources"]:
        if (skills[skill], title) in have:
            continue
        rid = client.call(
            "POST",
            "/admin/learning-resources",
            {
                "skill_id": skills[skill],
                "title": title,
                "url": url,
                "description": "Starter resource. Review before relying on it.",
            },
        )["id"]
        client.call("POST", f"/admin/learning-resources/{rid}/approve")
        count("learning resources (approved)")

    prompts = {q["prompt"] for q in client.call("GET", "/admin/interview-questions")}
    for skill, competency, prompt, min_words, rubric in pack["interview_questions"]:
        if prompt in prompts:
            continue
        client.call(
            "POST",
            "/admin/interview-questions",
            {
                "role_id": None,
                "skill_id": skills[skill] if skill else None,
                "competency": competency,
                "prompt": prompt,
                "min_words": min_words,
                "rubric": [{"concept": c, "keywords": kws, "weight": w} for c, kws, w in rubric],
            },
        )
        count("interview questions")

    sample = pack.get("sample_company")
    job = pack.get("sample_job")
    if sample and job:
        companies = {c["name"]: c["id"] for c in client.call("GET", "/admin/companies")}
        if sample["name"] not in companies:
            companies[sample["name"]] = client.call("POST", "/admin/companies", sample)["id"]
            count("sample company")
        if job["title"] not in {j["title"] for j in client.call("GET", "/admin/jobs")}:
            jid = client.call(
                "POST",
                "/admin/jobs",
                {
                    "company_id": companies[sample["name"]],
                    "title": job["title"],
                    "body": job["body"],
                    "role_id": roles[job["role"]],
                    "application_deadline": None,
                },
            )["id"]
            client.call(
                "PUT",
                f"/admin/jobs/{jid}/skills",
                [
                    {"skill_id": skills[s], "required_level": lvl, "weight": w}
                    for s, lvl, w in job["skills"]
                ],
            )
            el = job["eligibility"]
            client.call(
                "PUT",
                f"/admin/jobs/{jid}/eligibility",
                {
                    "cgpa_min": el["cgpa_min"],
                    "cgpa_basis": el["cgpa_basis"],
                    "max_arrears": el["max_arrears"],
                    "attendance_min": el["attendance_min"],
                    "department_ids": [departments[c] for c in el["departments"]],
                    "graduation_years": el["graduation_years"],
                    "custom_notes": None,
                },
            )
            count("sample job (draft, not published)")
    return made


def main() -> int:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--email", required=True, help="college admin email")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    args = parser.parse_args()
    password = os.environ.get("ADMIN_PASSWORD")
    if not password:
        logger.error("Set ADMIN_PASSWORD in the environment.")
        return 2
    pack = json.loads(args.pack.read_text(encoding="utf-8"))
    client = Client(args.base_url)
    try:
        client.login(args.email, password)
        made = load(client, pack)
    except ApiError as exc:
        logger.error("Failed: %s", exc)
        return 1
    if not made:
        logger.info("Nothing to do: everything in the pack already exists.")
    for kind, n in made.items():
        logger.info("created %d %s", n, kind)
    logger.info("Notice: %s", pack.get("notice", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
