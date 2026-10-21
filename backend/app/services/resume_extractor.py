"""Deterministic rules-based resume extractor (extractor_version "rules-1"). Pure: no I/O, no LLM.

The LLM-based extractor is Not implemented in this phase.

Assumptions (all deliberate; nothing is inferred or invented):
* Every extracted fact carries a span {start, end, text} where text == extracted_text[start:end].
* Section headings are whole lines (<= 40 chars) whose text, lower-cased and stripped of
  surrounding punctuation/colon, equals a known alias (education, experience, work experience,
  projects, skills, technical skills, certifications, certificates, ...). Other well-known
  headings (summary, objective, achievements, ...) only terminate the previous section.
  sections_found lists the display names in order of first appearance.
* Skills are only the skill names configured for the college, matched case-insensitively anywhere
  in the text. A match must not be glued to other word characters; names ending in a letter or
  digit also reject a following '+', '#' or '.<word char>' (so "C" does not match "C++", "C#"
  or "Node" in "Node.js"); names starting with a word char reject a preceding "<word>.".
* Education/projects/experience/certifications are raw text blocks of the matching section's body.
  Blocks split on blank lines and at lines starting with a bullet marker; other lines continue the
  current block. No degree/year/employer interpretation. A block span is trimmed of whitespace.
* role_match percent = sum(weight of found) / sum(weight of all role skills) * 100, 2dp;
  null when the role has no skills (or no text). jd_match percent = in-resume / in-JD * 100;
  null when no configured skill appears in the JD (or no text).
"""
import re
from collections.abc import Sequence
from typing import Any, TypedDict

EXTRACTOR_VERSION = "rules-1"

Span = dict[str, Any]

SECTION_ALIASES: dict[str, str] = {
    "education": "Education",
    "academic background": "Education",
    "academics": "Education",
    "experience": "Experience",
    "work experience": "Experience",
    "professional experience": "Experience",
    "internships": "Experience",
    "internship experience": "Experience",
    "employment history": "Experience",
    "projects": "Projects",
    "academic projects": "Projects",
    "personal projects": "Projects",
    "skills": "Skills",
    "technical skills": "Skills",
    "key skills": "Skills",
    "core competencies": "Skills",
    "certifications": "Certifications",
    "certificates": "Certifications",
    "certification": "Certifications",
    "licenses & certifications": "Certifications",
}
OTHER_HEADINGS = {
    "summary", "profile", "objective", "career objective", "professional summary", "achievements",
    "awards", "interests", "hobbies", "languages", "references", "declaration",
    "extracurricular activities", "publications", "contact", "personal details",
}
BULLET_RE = re.compile(r"^\s*(?:[•●▪◦‣–—*\-·]|\d+[.)])\s+")


class RoleSkillIn(TypedDict):
    """Role skill requirement input."""

    skill_id: int
    skill_name: str
    required_level: float
    weight: float


def _heading_key(line: str) -> str | None:
    stripped = line.strip().strip(":-_=*#| ").lower()
    if not stripped or len(line.strip()) > 40:
        return None
    return stripped


def _lines(text: str) -> list[tuple[int, int]]:
    """(start, end) offsets of each line, excluding the newline."""
    out: list[tuple[int, int]] = []
    pos = 0
    for raw in text.split("\n"):
        out.append((pos, pos + len(raw)))
        pos += len(raw) + 1
    return out


def _span(text: str, start: int, end: int) -> Span:
    return {"start": start, "end": end, "text": text[start:end]}


def find_sections(text: str) -> list[tuple[str, int, int]]:
    """Return (display name, body_start, body_end) for each known section heading."""
    lines = _lines(text)
    marks: list[tuple[int, int, str | None]] = []  # (line index, body start, canonical|None)
    for idx, (s, e) in enumerate(lines):
        key = _heading_key(text[s:e])
        if key is None:
            continue
        if key in SECTION_ALIASES:
            marks.append((idx, e, SECTION_ALIASES[key]))
        elif key in OTHER_HEADINGS:
            marks.append((idx, e, None))
    sections: list[tuple[str, int, int]] = []
    for n, (_idx, body_start, name) in enumerate(marks):
        if name is None:
            continue
        body_end = lines[marks[n + 1][0]][0] if n + 1 < len(marks) else len(text)
        sections.append((name, body_start, body_end))
    return sections


def split_blocks(text: str, start: int, end: int) -> list[Span]:
    """Split text[start:end] into raw blocks (blank-line / bullet separated), trimmed."""
    blocks: list[tuple[int, int]] = []
    cur: tuple[int, int] | None = None
    pos = start
    for raw in text[start:end].split("\n"):
        line_s = pos
        pos = line_s + len(raw) + 1
        if not raw.strip():
            if cur:
                blocks.append(cur)
            cur = None
            continue
        content_s = line_s + (len(raw) - len(raw.lstrip()))
        content_e = line_s + len(raw.rstrip())
        if cur is None or BULLET_RE.match(raw):
            if cur:
                blocks.append(cur)
            cur = (content_s, content_e)
        else:
            cur = (cur[0], content_e)
    if cur:
        blocks.append(cur)
    return [_span(text, s, e) for s, e in blocks]


def _skill_pattern(name: str) -> re.Pattern[str]:
    name = name.strip()
    body = re.escape(name)
    before = r"(?<!\w)"
    after = r"(?!\w)"
    if re.match(r"\w", name):
        before += r"(?<!\w\.)"
    if re.search(r"\w$", name):
        after = r"(?![\w+#]|\.\w)"
    return re.compile(before + body + after, re.IGNORECASE)


def find_skills(text: str, skills: Sequence[tuple[int, str]]) -> list[dict[str, Any]]:
    """Configured skills present in text, each with all occurrence spans (ordered by first hit)."""
    found: list[dict[str, Any]] = []
    for skill_id, name in skills:
        if not name.strip():
            continue
        spans = [_span(text, m.start(), m.end()) for m in _skill_pattern(name).finditer(text)]
        if spans:
            found.append({"skill_id": skill_id, "skill_name": name, "spans": spans})
    found.sort(key=lambda s: (s["spans"][0]["start"], s["skill_id"]))
    return found


def extract(text: str, skills: Sequence[tuple[int, str]]) -> dict[str, Any]:
    """Extract sections, skills and raw blocks from resume text."""
    result: dict[str, Any] = {
        "sections_found": [],
        "skills": find_skills(text, skills),
        "education": [],
        "projects": [],
        "experience": [],
        "certifications": [],
    }
    for name, s, e in find_sections(text):
        if name not in result["sections_found"]:
            result["sections_found"].append(name)
        key = name.lower()
        if key in ("education", "projects", "experience", "certifications"):
            for span in split_blocks(text, s, e):
                result[key].append({"text": span["text"], "span": span})
    return result


def _pct(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator * 100, 2)


def role_match(resume_skill_ids: set[int], role_skills: Sequence[RoleSkillIn]) -> dict[str, Any]:
    """Weighted coverage of the role's skills by the resume."""
    found = [r for r in role_skills if r["skill_id"] in resume_skill_ids]
    missing = [r for r in role_skills if r["skill_id"] not in resume_skill_ids]
    total = sum(r["weight"] for r in role_skills)
    return {
        "match_percent": _pct(sum(r["weight"] for r in found), total),
        "found": [dict(r) for r in found],
        "missing": [dict(r) for r in missing],
    }


def jd_match(
    jd_text: str, skills: Sequence[tuple[int, str]], resume_skill_ids: set[int]
) -> dict[str, Any]:
    """Configured skills appearing in the job description and whether the resume has them."""
    items = [
        {
            "skill_id": s["skill_id"],
            "skill_name": s["skill_name"],
            "in_resume": s["skill_id"] in resume_skill_ids,
        }
        for s in find_skills(jd_text, skills)
    ]
    return {
        "match_percent": _pct(sum(1 for i in items if i["in_resume"]), len(items)),
        "skills_in_jd": items,
    }
