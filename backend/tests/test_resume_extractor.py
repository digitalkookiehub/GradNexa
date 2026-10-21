"""Unit tests for the pure rules-based resume extractor."""
from app.services import resume_extractor as rx
from app.services.resume_extractor import RoleSkillIn

SAMPLE = """John Doe
john@example.com

Summary
Keen developer.

EDUCATION:
B.Tech Computer Science, XYZ University 2024
CGPA 8.1

Work Experience
- Built APIs with Python and SQL at Acme
  deployed on AWS
- Wrote C++ and C# services, plus .NET tooling

Projects
Chat app using Node.js and React

Weather CLI in python

Technical Skills
Python, SQL, C++, C#, .NET, Java, JavaScript

Certifications
AWS Certified Cloud Practitioner
"""

SKILLS = [
    (1, "Python"), (2, "SQL"), (3, "C++"), (4, "C#"), (5, ".NET"), (6, "Java"),
    (7, "JavaScript"), (8, "C"), (9, "Node"), (10, "React"), (11, "Rust"), (12, "AWS"),
]


def _check_spans(text: str, result: dict) -> None:  # type: ignore[type-arg]
    for s in result["skills"]:
        for sp in s["spans"]:
            assert text[sp["start"]: sp["end"]] == sp["text"]
    for key in ("education", "projects", "experience", "certifications"):
        for b in result[key]:
            sp = b["span"]
            assert text[sp["start"]: sp["end"]] == sp["text"] == b["text"]


def test_spans_index_back_to_text() -> None:
    result = rx.extract(SAMPLE, SKILLS)
    _check_spans(SAMPLE, result)
    py = next(s for s in result["skills"] if s["skill_name"] == "Python")
    assert len(py["spans"]) == 3  # case-insensitive, all occurrences
    assert {sp["text"].lower() for sp in py["spans"]} == {"python"}


def test_symbol_skills_and_word_boundaries() -> None:
    result = rx.extract(SAMPLE, SKILLS)
    names = {s["skill_name"]: s for s in result["skills"]}
    assert "C++" in names and "C#" in names and ".NET" in names
    assert len(names["C++"]["spans"]) == 2
    # bare "C" must not match inside C++ / C# / Certifications etc.
    assert "C" not in names
    # "Java" must not match inside JavaScript; JavaScript present once
    assert len(names["Java"]["spans"]) == 1
    assert len(names["JavaScript"]["spans"]) == 1
    # "Node" must not match Node.js
    assert "Node" not in names
    # not configured or absent => never invented
    assert "Rust" not in names
    assert all(s["skill_id"] in {i for i, _ in SKILLS} for s in result["skills"])


def test_no_skill_invented_when_none_configured() -> None:
    assert rx.extract(SAMPLE, [])["skills"] == []


def test_sections_and_blocks() -> None:
    result = rx.extract(SAMPLE, SKILLS)
    assert result["sections_found"] == [
        "Education", "Experience", "Projects", "Skills", "Certifications",
    ]
    assert [b["text"] for b in result["education"]] == [
        "B.Tech Computer Science, XYZ University 2024\nCGPA 8.1"
    ]
    assert len(result["experience"]) == 2  # bullets split blocks
    assert result["experience"][0]["text"].endswith("deployed on AWS")
    assert len(result["projects"]) == 2  # blank-line split
    assert result["certifications"][0]["text"] == "AWS Certified Cloud Practitioner"


def test_no_headings_gives_no_sections() -> None:
    result = rx.extract("just some Python text", SKILLS)
    assert result["sections_found"] == []
    assert result["education"] == []
    assert len(result["skills"]) == 1


def test_empty_text() -> None:
    result = rx.extract("", SKILLS)
    assert result["skills"] == [] and result["sections_found"] == []


def _rs(sid: int, name: str, weight: float) -> RoleSkillIn:
    return RoleSkillIn(skill_id=sid, skill_name=name, required_level=50.0, weight=weight)


def test_role_match_math() -> None:
    skills = [_rs(1, "Python", 3), _rs(2, "SQL", 1), _rs(11, "Rust", 2)]
    m = rx.role_match({1, 2}, skills)
    assert m["match_percent"] == round(4 / 6 * 100, 2) == 66.67
    assert [r["skill_id"] for r in m["found"]] == [1, 2]
    assert [r["skill_id"] for r in m["missing"]] == [11]
    assert rx.role_match(set(), skills)["match_percent"] == 0.0
    assert rx.role_match({1}, [])["match_percent"] is None


def test_jd_match_math() -> None:
    jd = "We need Python, SQL and Rust experience"
    m = rx.jd_match(jd, SKILLS, {1, 2})
    assert m["match_percent"] == 66.67
    by = {s["skill_name"]: s["in_resume"] for s in m["skills_in_jd"]}
    assert by == {"Python": True, "SQL": True, "Rust": False}
    assert rx.jd_match("nothing relevant", SKILLS, {1})["match_percent"] is None


def test_determinism() -> None:
    assert rx.extract(SAMPLE, SKILLS) == rx.extract(SAMPLE, SKILLS)
    assert rx.EXTRACTOR_VERSION == "rules-1"
