"""Lexical retrieval (BM25) over a college's APPROVED knowledge chunks.

Vector / embedding search: Not implemented in this phase (no embedding provider configured).
Retrieval is deterministic and every returned passage is a real stored chunk (never generated).

Public interface (used by the assistant orchestrator): :func:`search`.
Assumptions (unconfirmed, configurable): BM25 k1=1.5, b=0.75; an answer needs the best passage to
cover at least ``RAG_MIN_QUERY_COVERAGE`` (default 0.5) of the distinct non-stopword query terms.
"""
import math
import re
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import RAGChunk, RAGDocument, RagDocumentStatus

INSUFFICIENT_MESSAGE = "I don't have enough approved information to answer this confidently."
MAX_TOP_K = 10
SNIPPET_CHARS = 400
K1 = 1.5
B = 0.75

STOPWORDS = frozenset(
    "a an the and or but if of to in on at by for with from as is are was were be been being "
    "am do does did done have has had it its this that these those i me my we our you your he "
    "she they them their what which who whom whose when where why how can could should would "
    "will shall may might must not no so than then there here about into over under also just "
    "any some such very more most".split()
)
_TOKEN = re.compile(r"\.?[a-z0-9]+(?:[+#]+)?(?:\.[a-z0-9]+)*")


@dataclass(frozen=True)
class Passage:
    """A retrieved, citable passage (a real stored chunk)."""

    document_id: int
    document_title: str
    source_type: str
    chunk_id: int
    chunk_index: int
    snippet: str
    score: float
    query_coverage: float


@dataclass(frozen=True)
class SearchResult:
    """Search outcome. ``passages`` is empty when evidence is insufficient."""

    insufficient_evidence: bool
    message: str | None
    passages: list[Passage] = field(default_factory=list)


def _stem(token: str) -> str:
    """Minimal plural folding (deterministic, no dictionary)."""
    if not token.isalnum():
        return token
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens; keeps c++, c#, .net, node.js style tokens; no stopwords."""
    out: list[str] = []
    for raw in _TOKEN.findall(text.lower()):
        if raw in STOPWORDS:
            continue
        out.append(_stem(raw))
    return out


def bm25_scores(query_terms: list[str], docs: list[list[str]]) -> list[float]:
    """BM25 score of each tokenised doc for the distinct query terms."""
    n = len(docs)
    if n == 0:
        return []
    terms = sorted(set(query_terms))
    avg_len = (sum(len(d) for d in docs) / n) or 1.0
    df: Counter[str] = Counter()
    tfs: list[Counter[str]] = []
    for d in docs:
        tf = Counter(d)
        tfs.append(tf)
        for t in terms:
            if t in tf:
                df[t] += 1
    scores: list[float] = []
    for d, tf in zip(docs, tfs, strict=True):
        s = 0.0
        for t in terms:
            f = tf.get(t, 0)
            if not f:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * f * (K1 + 1) / (f + K1 * (1 - B + B * len(d) / avg_len))
        scores.append(s)
    return scores


def coverage(query_terms: list[str], doc_tokens: list[str]) -> float:
    """Fraction of distinct query terms present in the doc."""
    terms = set(query_terms)
    if not terms:
        return 0.0
    return len(terms & set(doc_tokens)) / len(terms)


def make_snippet(content: str, query_terms: list[str]) -> str:
    """<= 400 chars of the real chunk text, positioned around the first matching term."""
    if len(content) <= SNIPPET_CHARS:
        return content
    lowered = content.lower()
    pos = min((i for t in set(query_terms) if (i := lowered.find(t)) >= 0), default=0)
    start = max(0, pos - 80)
    while start > 0 and not content[start - 1].isspace():
        start -= 1
    end = min(len(content), start + SNIPPET_CHARS)
    if end < len(content):
        while end > start and not content[end].isspace():
            end -= 1
        if end == start:
            end = start + SNIPPET_CHARS
    return content[start:end].strip()


@dataclass(frozen=True)
class Candidate:
    """A loaded chunk with its document metadata (input to the pure ranker)."""

    document_id: int
    document_title: str
    source_type: str
    chunk_id: int
    chunk_index: int
    content: str


def rank(
    query: str, candidates: list[Candidate], top_k: int, min_coverage: float
) -> SearchResult:
    """Pure ranking + insufficient-evidence rule over already-loaded candidates."""
    terms = sorted(set(tokenize(query)))
    top_k = max(1, min(top_k, MAX_TOP_K))
    insufficient = SearchResult(True, INSUFFICIENT_MESSAGE, [])
    if not terms or not candidates:
        return insufficient
    docs = [tokenize(c.content) for c in candidates]
    scores = bm25_scores(terms, docs)
    scored = [
        (s, coverage(terms, d), c)
        for s, d, c in zip(scores, docs, candidates, strict=True)
        if s > 0
    ]
    scored.sort(key=lambda x: (-x[0], x[2].document_id, x[2].chunk_index))
    if not scored or max(cov for _, cov, _ in scored) < min_coverage:
        return insufficient
    passages = [
        Passage(
            document_id=c.document_id,
            document_title=c.document_title,
            source_type=c.source_type,
            chunk_id=c.chunk_id,
            chunk_index=c.chunk_index,
            snippet=make_snippet(c.content, terms),
            score=round(s, 4),
            query_coverage=round(cov, 4),
        )
        for s, cov, c in scored
        if cov >= min_coverage
    ][:top_k]
    return SearchResult(False, None, passages)


def load_candidates(
    db: Session, college_id: int, department_id: int | None, all_departments: bool
) -> list[Candidate]:
    """APPROVED chunks of the college visible to the caller's department."""
    stmt = (
        select(
            RAGDocument.id, RAGDocument.title, RAGDocument.source_type,
            RAGChunk.id, RAGChunk.chunk_index, RAGChunk.content,
        )
        .join(RAGChunk, RAGChunk.document_id == RAGDocument.id)
        .where(
            RAGDocument.college_id == college_id,
            RAGChunk.college_id == college_id,
            RAGDocument.status == RagDocumentStatus.APPROVED,
        )
        .order_by(RAGDocument.id, RAGChunk.chunk_index)
    )
    if not all_departments:
        if department_id is None:
            stmt = stmt.where(RAGDocument.department_id.is_(None))
        else:
            stmt = stmt.where(
                or_(
                    RAGDocument.department_id.is_(None),
                    RAGDocument.department_id == department_id,
                )
            )
    return [
        Candidate(d, t, getattr(st, "value", str(st)), cid, ci, content)
        for d, t, st, cid, ci, content in db.execute(stmt).all()
    ]


def search(
    db: Session,
    *,
    college_id: int,
    department_id: int | None,
    query: str,
    top_k: int = 5,
    all_departments: bool = False,
) -> SearchResult:
    """BM25 search over approved chunks of ``college_id``.

    ``all_departments=True`` ignores ``department_id`` (staff view); otherwise only documents with
    no department or the caller's department are visible. Returns insufficient_evidence with the
    exact message and no passages when the best match covers too few query terms.
    """
    candidates = load_candidates(db, college_id, department_id, all_departments)
    return rank(query, candidates, top_k, settings.RAG_MIN_QUERY_COVERAGE)
