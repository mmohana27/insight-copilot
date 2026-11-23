"""Hybrid retrieval: vector search + keyword search -> RRF fusion -> optional cross-encoder rerank."""
import os
import re
import sys
from functools import lru_cache
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector
from psycopg2.extras import RealDictCursor
from sentence_transformers import CrossEncoder, SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
CANDIDATES = 15   # how many results each search method returns before fusion
RERANK_POOL = 10  # how many fused results the reranker re-sorts
RRF_K = 60        # standard constant for Reciprocal Rank Fusion


@lru_cache(maxsize=1)
def _embedder():
    return SentenceTransformer(EMBED_MODEL)


@lru_cache(maxsize=1)
def _reranker():
    return CrossEncoder(RERANK_MODEL)


@lru_cache(maxsize=1)
def _conn():
    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    conn.autocommit = True
    register_vector(conn)
    return conn


def _fetch(sql: str, params: tuple) -> list[dict]:
    with _conn().cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def vector_search(query: str, n: int = CANDIDATES) -> list[dict]:
    """Search by meaning."""
    qvec = _embedder().encode(query, normalize_embeddings=True)
    return _fetch(
        """
        SELECT chunk_id, file_name, chunk_index, content
        FROM rag.chunks
        ORDER BY embedding <=> %s
        LIMIT %s
        """,
        (qvec, n),
    )


def keyword_search(query: str, n: int = CANDIDATES) -> list[dict]:
    """Search by exact words (Postgres full-text search). Any word may match (OR)."""
    terms = re.findall(r"[A-Za-z0-9]+", query.lower())
    if not terms:
        return []
    tsquery = " | ".join(terms)
    return _fetch(
        """
        SELECT chunk_id, file_name, chunk_index, content
        FROM rag.chunks
        WHERE content_tsv @@ to_tsquery('english', %s)
        ORDER BY ts_rank(content_tsv, to_tsquery('english', %s)) DESC
        LIMIT %s
        """,
        (tsquery, tsquery, n),
    )


def _fuse(*ranked_lists: list[dict]) -> list[dict]:
    """Reciprocal Rank Fusion: a chunk scores higher the nearer the top it is in each list."""
    scores, items = {}, {}
    for ranked in ranked_lists:
        for rank, row in enumerate(ranked, start=1):
            cid = row["chunk_id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank)
            items[cid] = row
    ordered = sorted(scores, key=scores.get, reverse=True)
    return [dict(items[c], score=scores[c]) for c in ordered]


def search(query: str, k: int = 3, mode: str = "hybrid_rerank") -> list[dict]:
    if mode not in ("vector", "hybrid", "hybrid_rerank"):
        raise ValueError(f"Unknown mode: {mode}")
    if mode == "vector":
        return vector_search(query, k)

    fused = _fuse(vector_search(query), keyword_search(query))
    if mode == "hybrid":
        return fused[:k]

    pool = fused[:RERANK_POOL]
    scores = _reranker().predict([(query, r["content"]) for r in pool])
    for row, score in zip(pool, scores):
        row["score"] = float(score)
    return sorted(pool, key=lambda r: r["score"], reverse=True)[:k]


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "Which campaign ran around Black Friday?"
    print(f'Q: "{q}"')
    for r in search(q, k=3):
        print(f"  {r['score']:.3f}  {r['file_name']:<38} {r['content'][:110]}...")