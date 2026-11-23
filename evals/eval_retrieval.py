"""Measure retrieval quality for three methods: vector, hybrid, hybrid + rerank."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from rag.retriever import search  # noqa: E402

QUESTIONS = json.loads((ROOT / "evals" / "retrieval_questions.json").read_text(encoding="utf-8"))
MODES = ["vector", "hybrid", "hybrid_rerank"]
K = 3


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def first_correct_rank(results, q):
    """Index of the first result that is from an expected file AND contains the key phrase."""
    for i, r in enumerate(results):
        if r["file_name"] in q["files"] and norm(q["must_contain"]) in norm(r["content"]):
            return i
    return None


def main():
    n = len(QUESTIONS)
    print(f"{n} questions, top-{K} results per question\n")
    print(f"{'method':<16}{'right file':>12}{'right chunk @1':>17}{'right chunk @3':>17}")
    misses = []

    for mode in MODES:
        file_hits = chunk_at_1 = chunk_at_3 = 0
        for q in QUESTIONS:
            results = search(q["question"], k=K, mode=mode)
            if any(r["file_name"] in q["files"] for r in results):
                file_hits += 1
            rank = first_correct_rank(results, q)
            if rank == 0:
                chunk_at_1 += 1
            if rank is not None:
                chunk_at_3 += 1
            elif mode == "hybrid_rerank":
                misses.append((q["question"], q["must_contain"], [r["file_name"] for r in results]))
        print(f"{mode:<16}{file_hits / n:>12.0%}{chunk_at_1 / n:>17.0%}{chunk_at_3 / n:>17.0%}")

    if misses:
        print("\nQuestions the best method still missed:")
        for question, phrase, files in misses:
            print(f'  - "{question}"  (needed: "{phrase}")  got: {files}')


if __name__ == "__main__":
    main()