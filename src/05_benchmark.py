import argparse
import csv
import re
from pathlib import Path
from statistics import mean
from typing import Dict, List

from rag_lib import answer_flat_rag, answer_graphrag

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"

QUESTIONS_PATH = DATA_DIR / "benchmark_questions.csv"
RESULTS_PATH = OUTPUT_DIR / "benchmark_results.csv"
REPORT_PATH = OUTPUT_DIR / "report.md"


REFUSAL_PATTERNS = [
    "cannot answer",
    "cannot provide",
    "does not provide",
    "does not contain",
    "insufficient",
    "not enough information",
]


def parse_keyword_groups(expr: str) -> List[List[str]]:
    """
    Parse expected keywords as AND-of-OR groups.
    Example:
    - "openai" -> [["openai"]]
    - "anthropic|databricks;openai" -> [["anthropic","databricks"],["openai"]]
    """
    groups: List[List[str]] = []
    for grp in (expr or "").split(";"):
        alts = [x.strip().lower() for x in grp.split("|") if x.strip()]
        if alts:
            groups.append(alts)
    return groups


def has_refusal(answer: str) -> bool:
    ans = (answer or "").lower()
    return any(p in ans for p in REFUSAL_PATTERNS)


def contains_keyword(answer: str, keyword: str) -> bool:
    ans = (answer or "").lower()
    kw = (keyword or "").strip().lower()
    if not kw:
        return False
    if re.fullmatch(r"[a-z0-9 .-]+", kw):
        pattern = rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])"
        return re.search(pattern, ans) is not None
    return kw in ans


def score_answer(answer: str, expected_keywords: str) -> int:
    answer_l = (answer or "").lower()
    if has_refusal(answer_l):
        return 0

    groups = parse_keyword_groups(expected_keywords)
    if not groups:
        return 0
    # all groups must match at least one alternative
    for group in groups:
        if not any(contains_keyword(answer_l, kw) for kw in group):
            return 0
    return 1


def run_one(system: str, question: str) -> Dict:
    if system == "flat":
        return answer_flat_rag(question)
    return answer_graphrag(question)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions-path", default=str(QUESTIONS_PATH))
    args = parser.parse_args()

    questions_path = Path(args.questions_path)
    if not questions_path.exists():
        raise FileNotFoundError(f"Missing benchmark file: {questions_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: List[Dict] = []

    with questions_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        questions = list(reader)

    for item in questions:
        qid = item.get("question_id", "")
        question = item.get("question", "")
        expected = item.get("expected_keywords", "")
        category = (item.get("category", "uncategorized") or "uncategorized").strip()
        for system in ("flat", "graph"):
            result = run_one(system, question)
            correct = score_answer(result.get("answer", ""), expected)
            rows.append(
                {
                    "question_id": qid,
                    "question": question,
                    "system": system,
                    "category": category,
                    "answer": result.get("answer", ""),
                    "correct": correct,
                    "latency_ms": result.get("latency_ms", 0),
                    "token_in": result.get("token_in", 0),
                    "token_out": result.get("token_out", 0),
                    "estimated_cost": result.get("estimated_cost", 0),
                }
            )
            print(f"[{qid}] {system} correct={correct}")

    with RESULTS_PATH.open("w", newline="", encoding="utf-8") as f:
        fields = [
            "question_id",
            "question",
            "system",
            "category",
            "answer",
            "correct",
            "latency_ms",
            "token_in",
            "token_out",
            "estimated_cost",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    flat = [r for r in rows if r["system"] == "flat"]
    graph = [r for r in rows if r["system"] == "graph"]

    def metrics(items: List[Dict]) -> Dict:
        return {
            "acc": mean(int(r["correct"]) for r in items) if items else 0.0,
            "latency": mean(float(r["latency_ms"]) for r in items) if items else 0.0,
            "tin": mean(float(r["token_in"]) for r in items) if items else 0.0,
            "tout": mean(float(r["token_out"]) for r in items) if items else 0.0,
            "cost": sum(float(r["estimated_cost"]) for r in items),
        }

    m_flat = metrics(flat)
    m_graph = metrics(graph)
    delta_acc = m_graph["acc"] - m_flat["acc"]

    categories = sorted({r["category"] for r in rows})
    cat_lines = []
    for cat in categories:
        flat_cat = [r for r in flat if r["category"] == cat]
        graph_cat = [r for r in graph if r["category"] == cat]
        if not flat_cat or not graph_cat:
            continue
        mf = metrics(flat_cat)
        mg = metrics(graph_cat)
        cat_lines.append(
            f"| {cat} | {mf['acc']:.2%} | {mg['acc']:.2%} | {(mg['acc'] - mf['acc']):.2%} |"
        )
    cat_table = "\n".join(cat_lines) if cat_lines else "| n/a | n/a | n/a | n/a |"

    report = f"""# GraphRAG Benchmark Report

| Metric | Flat RAG | GraphRAG | Delta |
|---|---:|---:|---:|
| Accuracy (20 Q) | {m_flat['acc']:.2%} | {m_graph['acc']:.2%} | {delta_acc:.2%} |
| Avg Latency (ms) | {m_flat['latency']:.1f} | {m_graph['latency']:.1f} | {m_graph['latency'] - m_flat['latency']:.1f} |
| Avg Input Tokens | {m_flat['tin']:.1f} | {m_graph['tin']:.1f} | {m_graph['tin'] - m_flat['tin']:.1f} |
| Avg Output Tokens | {m_flat['tout']:.1f} | {m_graph['tout']:.1f} | {m_graph['tout'] - m_flat['tout']:.1f} |
| Estimated Cost / 20 Q (USD) | {m_flat['cost']:.4f} | {m_graph['cost']:.4f} | {m_graph['cost'] - m_flat['cost']:.4f} |

## Accuracy by Category
| Category | Flat RAG | GraphRAG | Delta |
|---|---:|---:|---:|
{cat_table}

## Scoring Protocol (No Mock)
- Deterministic keyword scoring: `expected_keywords` is parsed as AND-of-OR groups.
- Any refusal-style answer (`cannot answer`, `insufficient`, etc.) is scored as incorrect.
- Both Flat RAG and GraphRAG are evaluated with the same scoring logic.

## Failure Modes
- Entity ambiguity in company names.
- Missing relation chains in extraction.
- Hallucination when retrieval context is weak.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"[Done] Results: {RESULTS_PATH}")
    print(f"[Done] Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
