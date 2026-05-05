import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"


def read_csv(path: Path) -> List[Dict]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_float(v) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def to_int(v) -> int:
    try:
        return int(float(v))
    except Exception:
        return 0


def metrics(rows: List[Dict]) -> Dict:
    return {
        "acc": mean(to_int(r.get("correct", 0)) for r in rows) if rows else 0.0,
        "latency": mean(to_float(r.get("latency_ms", 0)) for r in rows) if rows else 0.0,
        "tin": mean(to_float(r.get("token_in", 0)) for r in rows) if rows else 0.0,
        "tout": mean(to_float(r.get("token_out", 0)) for r in rows) if rows else 0.0,
        "cost": sum(to_float(r.get("estimated_cost", 0)) for r in rows),
    }


def first_target(expected_keywords: str) -> str:
    expr = (expected_keywords or "").strip().lower()
    if not expr:
        return "unknown"
    first_group = expr.split(";")[0]
    first_alt = first_group.split("|")[0].strip()
    return first_alt or "unknown"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default=str(OUTPUT_DIR / "benchmark_results.csv"))
    parser.add_argument("--questions", default=str(DATA_DIR / "benchmark_questions_strict.csv"))
    parser.add_argument("--output", default=str(OUTPUT_DIR / "report_detailed.md"))
    args = parser.parse_args()

    results_path = Path(args.results)
    questions_path = Path(args.questions)
    output_path = Path(args.output)

    rows = read_csv(results_path)
    by_qid: Dict[str, Dict[str, Dict]] = defaultdict(dict)
    for r in rows:
        by_qid[r["question_id"]][r["system"]] = r

    flat_rows = [r for r in rows if r["system"] == "flat"]
    graph_rows = [r for r in rows if r["system"] == "graph"]
    m_flat = metrics(flat_rows)
    m_graph = metrics(graph_rows)

    graph_win = []
    flat_win = []
    both_ok = []
    both_fail = []

    for qid, pair in sorted(by_qid.items()):
        flat = pair.get("flat")
        graph = pair.get("graph")
        if not flat or not graph:
            continue
        f = to_int(flat.get("correct", 0))
        g = to_int(graph.get("correct", 0))
        if g > f:
            graph_win.append((qid, flat.get("question", ""), flat.get("answer", ""), graph.get("answer", "")))
        elif f > g:
            flat_win.append((qid, flat.get("question", ""), flat.get("answer", ""), graph.get("answer", "")))
        elif f == 1:
            both_ok.append((qid, flat.get("question", "")))
        else:
            both_fail.append((qid, flat.get("question", "")))

    cat_stats = []
    categories = sorted({r.get("category", "uncategorized") for r in rows})
    for cat in categories:
        f_rows = [r for r in flat_rows if r.get("category", "") == cat]
        g_rows = [r for r in graph_rows if r.get("category", "") == cat]
        if not f_rows or not g_rows:
            continue
        mf = metrics(f_rows)
        mg = metrics(g_rows)
        cat_stats.append((cat, mf["acc"], mg["acc"], mg["acc"] - mf["acc"]))

    target_counter = Counter()
    if questions_path.exists():
        qrows = read_csv(questions_path)
        for q in qrows:
            target_counter[first_target(q.get("expected_keywords", ""))] += 1

    lines: List[str] = []
    lines.append("# Detailed Benchmark Analysis")
    lines.append("")
    lines.append("## 1) Key Metrics")
    lines.append(f"- Flat accuracy: **{m_flat['acc']:.2%}**")
    lines.append(f"- GraphRAG accuracy: **{m_graph['acc']:.2%}**")
    lines.append(f"- Delta accuracy: **{(m_graph['acc'] - m_flat['acc']):.2%}**")
    lines.append(f"- Avg latency delta (Graph-Flat): **{(m_graph['latency'] - m_flat['latency']):.1f} ms**")
    lines.append(f"- Total cost delta (Graph-Flat): **{(m_graph['cost'] - m_flat['cost']):.4f} USD**")
    lines.append("")
    lines.append("## 2) Pairwise Outcome")
    lines.append(f"- Graph wins: **{len(graph_win)}** questions")
    lines.append(f"- Flat wins: **{len(flat_win)}** questions")
    lines.append(f"- Both correct: **{len(both_ok)}** questions")
    lines.append(f"- Both incorrect: **{len(both_fail)}** questions")
    lines.append("")
    lines.append("## 3) Category Breakdown")
    for cat, af, ag, d in cat_stats:
        lines.append(f"- `{cat}`: Flat {af:.2%}, Graph {ag:.2%}, Delta {d:.2%}")
    lines.append("")
    lines.append("## 4) Graph-Win Cases")
    if graph_win:
        for qid, q, _, _ in graph_win:
            lines.append(f"- `{qid}` {q}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## 5) Flat-Win Cases")
    if flat_win:
        for qid, q, _, _ in flat_win:
            lines.append(f"- `{qid}` {q}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## 6) Reliability Check")
    lines.append("- Scoring is deterministic keyword matching with refusal filtering.")
    lines.append("- This is stricter than loose keyword scoring, but still not full semantic/path equivalence.")
    if target_counter:
        lines.append("- Expected target distribution in this benchmark:")
        for target, cnt in target_counter.most_common():
            lines.append(f"- `{target}`: {cnt} questions")
    lines.append("- If one target dominates heavily, results can look overly optimistic.")
    lines.append("")
    lines.append("## 7) Actionable Next Steps")
    lines.append("- Add path-level validation using `path_hint` to verify relation chains explicitly.")
    lines.append("- Add anti-overfit samples with balanced entities across Anthropic, Nvidia, Stability, Perplexity, OpenAI, Google, Databricks.")
    lines.append("- Keep a held-out benchmark file not touched during prompt/retrieval tuning.")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[Done] Wrote {output_path}")


if __name__ == "__main__":
    main()
