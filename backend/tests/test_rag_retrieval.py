"""BM25 unit tests and the golden retrieval evaluation (lexical retrieval only)."""
import pytest
from sqlalchemy.orm import Session

from app.models import (
    College,
    Department,
    RAGChunk,
    RAGDocument,
    RagDocumentStatus,
    RagSourceType,
    User,
)
from app.services import rag_chunker
from app.services.retrieval_service import (
    INSUFFICIENT_MESSAGE,
    Candidate,
    bm25_scores,
    coverage,
    make_snippet,
    rank,
    search,
    tokenize,
)

# ---------------------------------------------------------------- tokenizer / BM25


def test_tokenize_keeps_tech_tokens_and_drops_stopwords() -> None:
    toks = tokenize("What is the C++ and C# difference, .NET and Node.js?")
    assert "c++" in toks and "c#" in toks and ".net" in toks and "node.js" in toks
    assert "what" not in toks and "the" not in toks
    assert tokenize("End of sentence.") == ["end", "sentence"]


def test_tokenize_plural_folding() -> None:
    assert tokenize("tables") == tokenize("table")
    assert tokenize("queries") == tokenize("query")
    assert tokenize("class") == ["class"]


def test_bm25_prefers_rarer_and_more_frequent_terms() -> None:
    docs = [
        ["sql", "join", "join", "table"],
        ["sql", "table", "index"],
        ["resume", "photo"],
    ]
    scores = bm25_scores(["join"], docs)
    assert scores[0] > 0 and scores[1] == 0 and scores[2] == 0
    both = bm25_scores(["sql", "join"], docs)
    assert both[0] > both[1] > both[2] == 0


def test_bm25_length_normalisation() -> None:
    short = ["join", "table"]
    long = ["join"] + ["filler"] * 50
    s = bm25_scores(["join"], [short, long])
    assert s[0] > s[1]


def test_bm25_empty_inputs() -> None:
    assert bm25_scores(["a"], []) == []
    assert bm25_scores([], [["a"]]) == [0.0]


def test_coverage() -> None:
    assert coverage(["a", "b"], ["a", "x"]) == 0.5
    assert coverage([], ["a"]) == 0.0


def test_snippet_bounded_and_real_text() -> None:
    content = ("alpha " * 100) + "needle " + ("omega " * 100)
    snip = make_snippet(content, ["needle"])
    assert len(snip) <= 400 and "needle" in snip and snip in content
    assert make_snippet("short", ["x"]) == "short"


def _cand(i: int, text: str) -> Candidate:
    return Candidate(i, f"Doc {i}", "OTHER", i * 10, 0, text)


def test_rank_is_deterministic_and_caps_top_k() -> None:
    cands = [_cand(i, "sql join table example") for i in range(1, 15)]
    first = rank("sql join", cands, 50, 0.5)
    assert len(first.passages) == 10
    assert first == rank("sql join", cands, 50, 0.5)
    assert [p.document_id for p in first.passages] == list(range(1, 11))


def test_rank_insufficient_cases() -> None:
    cands = [_cand(1, "sql join table")]
    assert rank("", cands, 5, 0.5).insufficient_evidence
    assert rank("the of and", cands, 5, 0.5).insufficient_evidence
    assert rank("sql", [], 5, 0.5).message == INSUFFICIENT_MESSAGE
    # only 1 of 4 terms matches: coverage 0.25 < 0.5
    assert rank("sql oceans volcano weather", cands, 5, 0.5).insufficient_evidence
    assert not rank("sql oceans", cands, 5, 0.5).insufficient_evidence


# ---------------------------------------------------------------- golden corpus

CORPUS: dict[str, tuple[RagSourceType, str]] = {
    "SQL Joins and Queries": (
        RagSourceType.LEARNING_MATERIAL,
        "# SQL Joins\n\nSQL joins combine rows from two or more tables. An INNER JOIN returns "
        "only the matching rows from both tables. A LEFT JOIN returns every row of the left "
        "table plus matching rows of the right table, filling missing values with NULL.\n\n"
        "# Aggregation\n\nGROUP BY groups rows so aggregate functions such as COUNT, SUM and AVG "
        "can summarise each group. HAVING filters groups after aggregation while WHERE filters "
        "rows before it.\n\n# Indexes\n\nAn index speeds up SELECT queries on large tables.",
    ),
    "Data Structures and Algorithms": (
        RagSourceType.SYLLABUS,
        "# Data structures\n\nArrays, linked lists, stacks and queues are linear data "
        "structures. A binary search tree keeps keys ordered so lookup, insertion and deletion "
        "take logarithmic time on a balanced tree.\n\n# Sorting\n\nQuicksort has average time "
        "complexity O(n log n) and worst case O(n squared). Merge sort guarantees O(n log n).\n\n"
        "# Graphs\n\nBreadth first search and depth first search traverse a graph.",
    ),
    "Resume Writing Tips": (
        RagSourceType.PLACEMENT_GUIDE,
        "# Resume basics\n\nKeep your resume to one page. Start every bullet with a strong "
        "action verb such as built, designed or led. Quantify achievements with numbers.\n\n"
        "# Formatting\n\nAvoid photos, colourful graphics and tables because applicant tracking "
        "system parsers read plain text. Include ATS keywords from the job description.\n\n"
        "# Projects\n\nList two or three projects with the technologies used and your role.",
    ),
    "Interview Preparation Guide": (
        RagSourceType.INTERVIEW_GUIDE,
        "# Behavioural questions\n\nUse the STAR method: Situation, Task, Action and Result. "
        "It keeps behavioural interview answers structured and concise.\n\n# Introductions\n\n"
        "Prepare a short answer to the question tell me about yourself covering education, "
        "projects and goals.\n\n# Mock interviews\n\nPractise mock interviews with peers and "
        "review recordings to improve body language.",
    ),
    "Placement Policy": (
        RagSourceType.POLICY,
        "# Eligibility\n\nStudents need a minimum CGPA of 6.5 and no active backlogs to be "
        "eligible for campus placement drives.\n\n# Offers\n\nThe one offer policy lets a placed "
        "student sit for further drives only for a dream offer with a higher package.\n\n"
        "# Registration\n\nRegister on the placement portal before the drive deadline.",
    ),
    "Programming Languages Syllabus": (
        RagSourceType.SYLLABUS,
        "# Python\n\nPython topics: lists, dictionaries, object oriented programming with "
        "classes and inheritance, exception handling with try and except, file handling and "
        "decorators.\n\n# C++\n\nC++ topics: pointers, templates and the standard template "
        "library.",
    ),
    "Aptitude Preparation": (
        RagSourceType.LEARNING_MATERIAL,
        "# Quantitative aptitude\n\nPractise percentages, profit and loss, time and work, "
        "ratio and proportion and averages.\n\n# Reasoning\n\nLogical reasoning covers "
        "seating arrangements, series and syllogisms. Verbal ability covers grammar and "
        "reading comprehension.",
    ),
    "Database Management Systems": (
        RagSourceType.SYLLABUS,
        "# Transactions\n\nA transaction must satisfy the ACID properties: atomicity, "
        "consistency, isolation and durability.\n\n# Normalization\n\nNormalization reduces "
        "redundancy. Third normal form 3NF removes transitive dependencies.\n\n# Design\n\n"
        "ER diagrams model entities and relationships. B-tree indexing supports efficient "
        "lookups and concurrency control uses locking.",
    ),
}

GOLDEN: list[tuple[str, str]] = [
    ("how does a left join work in SQL", "SQL Joins and Queries"),
    ("difference between inner join and left join", "SQL Joins and Queries"),
    ("group by and having in aggregation", "SQL Joins and Queries"),
    ("what is a binary search tree", "Data Structures and Algorithms"),
    ("time complexity of quicksort", "Data Structures and Algorithms"),
    ("breadth first search on a graph", "Data Structures and Algorithms"),
    ("which action verbs should I use on my resume", "Resume Writing Tips"),
    ("should I include a photo in my resume", "Resume Writing Tips"),
    ("ATS keywords for the job description", "Resume Writing Tips"),
    ("what is the STAR method for interviews", "Interview Preparation Guide"),
    ("how to answer tell me about yourself", "Interview Preparation Guide"),
    ("minimum CGPA required for placement eligibility", "Placement Policy"),
    ("explain the one offer policy and dream offer", "Placement Policy"),
    ("python exception handling", "Programming Languages Syllabus"),
    ("profit and loss aptitude questions", "Aptitude Preparation"),
    ("ACID properties of a transaction", "Database Management Systems"),
    ("what is 3NF normalization", "Database Management Systems"),
]
OFF_TOPIC = [
    "weather forecast for Paris tomorrow",
    "best pizza recipe with extra cheese",
    "who won the football world cup",
    "how do I train a puppy",
]


def _seed(db: Session, college: College, status: RagDocumentStatus) -> dict[int, str]:
    user = db.query(User).filter(User.college_id == college.id).first()
    assert user is not None
    ids: dict[int, str] = {}
    for n, (title, (stype, text)) in enumerate(CORPUS.items()):
        doc = RAGDocument(
            college_id=college.id, title=title, source_type=stype, original_filename="x.md",
            content_type="text/markdown", size_bytes=len(text), sha256="0" * 64,
            storage_key=f"golden/{college.id}/{n}", status=status, uploaded_by=user.id,
        )
        db.add(doc)
        db.flush()
        chunks = rag_chunker.chunk_text(text, 400, 60)
        doc.chunk_count = len(chunks)
        for c in chunks:
            db.add(RAGChunk(
                document_id=doc.id, college_id=college.id, chunk_index=c.index,
                content=c.content, token_count=len(c.content.split()),
                char_start=c.char_start, char_end=c.char_end,
                chunk_metadata={"heading": c.heading},
            ))
        ids[doc.id] = title
    db.commit()
    return ids


@pytest.fixture
def golden(db: Session, college: College, make_user) -> dict[int, str]:  # type: ignore[no-untyped-def]
    make_user(college)
    return _seed(db, college, RagDocumentStatus.APPROVED)


def test_golden_recall_at_3(db: Session, college: College, golden: dict[int, str]) -> None:
    hits = 0
    misses: list[str] = []
    for query, expected in GOLDEN:
        res = search(db, college_id=college.id, department_id=None, query=query, top_k=3,
                     all_departments=True)
        titles = [p.document_title for p in res.passages]
        if expected in titles:
            hits += 1
        else:
            misses.append(f"{query} -> {titles}")
    recall = hits / len(GOLDEN)
    assert recall >= 0.9, (recall, misses)


def test_golden_top1_reasonable(db: Session, college: College, golden: dict[int, str]) -> None:
    top1 = 0
    for query, expected in GOLDEN:
        res = search(db, college_id=college.id, department_id=None, query=query, top_k=1,
                     all_departments=True)
        if res.passages and res.passages[0].document_title == expected:
            top1 += 1
    assert top1 / len(GOLDEN) >= 0.8


@pytest.mark.parametrize("query", OFF_TOPIC)
def test_off_topic_is_insufficient(
    db: Session, college: College, golden: dict[int, str], query: str
) -> None:
    res = search(db, college_id=college.id, department_id=None, query=query,
                 all_departments=True)
    assert res.insufficient_evidence is True
    assert res.message == "I don't have enough approved information to answer this confidently."
    assert res.passages == []


def test_citations_map_to_real_chunks(
    db: Session, college: College, golden: dict[int, str]
) -> None:
    for query, _ in GOLDEN:
        res = search(db, college_id=college.id, department_id=None, query=query, top_k=5,
                     all_departments=True)
        assert res.passages
        for p in res.passages:
            chunk = db.get(RAGChunk, p.chunk_id)
            assert chunk is not None
            assert chunk.document_id == p.document_id
            assert chunk.chunk_index == p.chunk_index
            assert p.snippet in chunk.content and len(p.snippet) <= 400
            doc = db.get(RAGDocument, p.document_id)
            assert doc is not None and doc.title == p.document_title
            assert doc.status == RagDocumentStatus.APPROVED
            assert 0 < p.query_coverage <= 1 and p.score > 0


def test_unapproved_never_retrievable(db: Session, college: College, make_user) -> None:  # type: ignore[no-untyped-def]
    make_user(college)
    _seed(db, college, RagDocumentStatus.PENDING)
    res = search(db, college_id=college.id, department_id=None, query="left join sql",
                 all_departments=True)
    assert res.insufficient_evidence


def test_department_visibility_at_service_level(
    db: Session, college: College, make_user  # type: ignore[no-untyped-def]
) -> None:
    user = make_user(college)
    d1 = Department(college_id=college.id, name="CS", code="CS")
    d2 = Department(college_id=college.id, name="EC", code="EC")
    db.add_all([d1, d2])
    db.commit()
    for key, dept in (("a", d1.id), ("b", d2.id), ("c", None)):
        doc = RAGDocument(
            college_id=college.id, title=f"Doc {key}", source_type=RagSourceType.OTHER,
            department_id=dept, original_filename="x.txt", content_type="text/plain",
            size_bytes=1, sha256="0" * 64, storage_key=f"k/{key}",
            status=RagDocumentStatus.APPROVED, uploaded_by=user.id, chunk_count=1,
        )
        db.add(doc)
        db.flush()
        db.add(RAGChunk(
            document_id=doc.id, college_id=college.id, chunk_index=0,
            content="compiler design lecture notes", token_count=4, char_start=0, char_end=29,
            chunk_metadata={},
        ))
    db.commit()

    def titles(dept: int | None, allx: bool = False) -> set[str]:
        res = search(db, college_id=college.id, department_id=dept,
                     query="compiler design notes", all_departments=allx)
        return {p.document_title for p in res.passages}

    assert titles(d1.id) == {"Doc a", "Doc c"}
    assert titles(None) == {"Doc c"}
    assert titles(None, True) == {"Doc a", "Doc b", "Doc c"}
