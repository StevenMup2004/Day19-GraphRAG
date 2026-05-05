import argparse
import csv
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


def score_answer(answer: str, expected_keywords: str) -> int:
    answer_l = (answer or "").lower()
    kws = [k.strip().lower() for k in expected_keywords.split(";") if k.strip()]
    if not kws:
        return 0
    return int(any(kw in answer_l for kw in kws))


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
        for system in ("flat", "graph"):
            result = run_one(system, question)
            correct = score_answer(result.get("answer", ""), expected)
            rows.append(
                {
                    "question_id": qid,
                    "question": question,
                    "system": system,
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

    report = f"""# GraphRAG Benchmark Report

| Metric | Flat RAG | GraphRAG | Delta |
|---|---:|---:|---:|
| Accuracy (20 Q) | {m_flat['acc']:.2%} | {m_graph['acc']:.2%} | {delta_acc:.2%} |
| Avg Latency (ms) | {m_flat['latency']:.1f} | {m_graph['latency']:.1f} | {m_graph['latency'] - m_flat['latency']:.1f} |
| Avg Input Tokens | {m_flat['tin']:.1f} | {m_graph['tin']:.1f} | {m_graph['tin'] - m_flat['tin']:.1f} |
| Avg Output Tokens | {m_flat['tout']:.1f} | {m_graph['tout']:.1f} | {m_graph['tout'] - m_flat['tout']:.1f} |
| Estimated Cost / 20 Q (USD) | {m_flat['cost']:.4f} | {m_graph['cost']:.4f} | {m_graph['cost'] - m_flat['cost']:.4f} |

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
