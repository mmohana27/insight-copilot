"""Ingest PDFs: extract text -> chunk -> embed -> store in pgvector (rag.chunks)."""
import os
import re
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector
from psycopg2.extras import execute_values
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "rag" / "docs"
load_dotenv(ROOT / ".env")

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIM = 384          # this model turns every text into 384 numbers
MAX_CHARS = 700          # target chunk size
OVERLAP_SENTENCES = 1    # last sentence of a chunk is repeated at the start of the next

DDL = f"""
CREATE TABLE IF NOT EXISTS rag.chunks (
    chunk_id      bigserial PRIMARY KEY,
    file_name     text        NOT NULL,
    doc_title     text        NOT NULL,
    chunk_index   int         NOT NULL,
    content       text        NOT NULL,
    embedding     vector({EMBED_DIM}) NOT NULL,
    content_tsv   tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    embedded_with text        NOT NULL,
    loaded_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (file_name, chunk_index)
);
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
    ON rag.chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_tsv_gin
    ON rag.chunks USING gin (content_tsv);
"""


def connect():
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def extract_text(path: Path) -> tuple[str, str]:
    """Return (title, clean_text) for one PDF."""
    reader = PdfReader(path)
    title = (reader.metadata.title if reader.metadata else None) or path.stem
    text = " ".join(page.extract_text() or "" for page in reader.pages)
    text = re.sub(r"\s+", " ", text).strip()                    # collapse line breaks and spaces
    text = re.sub(r"Owner:.*?portfolio project", "", text)      # drop the repeated header line
    text = text.replace(title, "", 1).strip()                   # title is added back to every chunk
    return title, text


def chunk_text(text: str) -> list[str]:
    """Pack whole sentences into chunks of about MAX_CHARS, with a one-sentence overlap."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    chunks, current, fresh = [], [], 0
    for sentence in sentences:
        if fresh and len(" ".join(current + [sentence])) > MAX_CHARS:
            chunks.append(" ".join(current))
            current = current[-OVERLAP_SENTENCES:] if OVERLAP_SENTENCES else []
            fresh = 0
        current.append(sentence)
        fresh += 1
    if fresh:
        chunks.append(" ".join(current))
    return chunks


def search(cur, model, query: str, k: int = 3):
    qvec = model.encode(query, normalize_embeddings=True)
    cur.execute(
        """
        SELECT file_name, content, 1 - (embedding <=> %s) AS similarity
        FROM rag.chunks
        ORDER BY embedding <=> %s
        LIMIT %s
        """,
        (qvec, qvec, k),
    )
    return cur.fetchall()


def main():
    pdfs = sorted(DOCS_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found in {DOCS_DIR}. Run rag/generate_docs.py first.")

    # 1) read and chunk
    records = []  # (file_name, title, chunk_index, content)
    for pdf in pdfs:
        title, text = extract_text(pdf)
        for i, chunk in enumerate(chunk_text(text)):
            records.append((pdf.name, title, i, f"{title}: {chunk}"))  # title gives each chunk context
    print(f"{len(pdfs)} PDFs -> {len(records)} chunks\n")

    # 2) embed (first run downloads the model, about 90 MB)
    print(f"Loading embedding model {MODEL_NAME} ...")
    model = SentenceTransformer(MODEL_NAME)
    assert model.get_sentence_embedding_dimension() == EMBED_DIM
    vectors = model.encode(
        [r[3] for r in records], batch_size=32, normalize_embeddings=True, show_progress_bar=True
    )

    # 3) store
    conn = connect()
    with conn, conn.cursor() as cur:
        cur.execute(DDL)
    register_vector(conn)  # lets psycopg2 send numpy arrays as pgvector values
    rows = [(f, t, i, c, v, MODEL_NAME) for (f, t, i, c), v in zip(records, vectors)]
    with conn, conn.cursor() as cur:
        cur.execute("TRUNCATE rag.chunks RESTART IDENTITY")  # full reload, safe to re-run
        execute_values(
            cur,
            "INSERT INTO rag.chunks (file_name, doc_title, chunk_index, content, embedding, embedded_with) VALUES %s",
            rows,
        )
    print(f"\nStored {len(rows)} chunks in rag.chunks\n")

    # 4) sanity check: semantic search
    queries = [
        "How do I send an item back?",
        "What happens if profit margin gets too low?",
        "Which campaign ran around Black Friday?",
    ]
    with conn, conn.cursor() as cur:
        for q in queries:
            print(f'Q: "{q}"')
            for file_name, content, sim in search(cur, model, q):
                print(f"   {sim:.3f}  {file_name:<38} {content[:90]}...")
            print()
    conn.close()


if __name__ == "__main__":
    main()