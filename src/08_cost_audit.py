import csv
import json
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"

CORPUS_PATH = DATA_DIR / "corpus_articles.jsonl"
ENTITIES_PATH = OUTPUT_DIR / "entities.csv"
TRIPLES_PATH = OUTPUT_DIR / "triples.csv"
BENCH_PATH = OUTPUT_DIR / "benchmark_results.csv"
OUT_PATH = OUTPUT_DIR / "cost_audit.md"

# Same chat price model used in rag_lib.py
CHAT_IN_PER_M = 0.15
CHAT_OUT_PER_M = 0.60
# Assumed embedding price for flat baseline indexing
EMBED_PER_M = 0.02


def read_jsonl(path: Path) -> List[Dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def old_chunk_text(text: str, max_chars: int = 3200) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: List[str] = []
    current: List[str] = []
    cur_len = 0
    for p in paragraphs:
        if len(p) > max_chars:
            p = p[:max_chars]
        if cur_len + len(p) + 1 > max_chars and current:
            chunks.append("\n".join(current))
            current = [p]
            cur_len = len(p)
        else:
            current.append(p)
            cur_len += len(p) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


def new_chunk_text(text: str, max_chars: int = 3200) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: List[str] = []
    current: List[str] = []
    cur_len = 0
    for p in paragraphs:
        parts = [p[i : i + max_chars] for i in range(0, len(p), max_chars)] or [p]
        for part in parts:
            if cur_len + len(part) + 1 > max_chars and current:
                chunks.append("\n".join(current))
                current = [part]
                cur_len = len(part)
            else:
                current.append(part)
                cur_len += len(part) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


def main() -> None:
    corpus = read_jsonl(CORPUS_PATH)
    entities = list(csv.DictReader(ENTITIES_PATH.open("r", encoding="utf-8")))
    triples = list(csv.DictReader(TRIPLES_PATH.open("r", encoding="utf-8")))
    bench = list(csv.DictReader(BENCH_PATH.open("r", encoding="utf-8")))

    old_chunks = []
    new_chunks = []
    for row in corpus:
        text = row.get("text", "")
        old_chunks.extend(old_chunk_text(text)[:2])
        new_chunks.extend(new_chunk_text(text)[:2])

    old_in_tokens = round(sum(len(c) for c in old_chunks) / 4)
    new_in_tokens = round(sum(len(c) for c in new_chunks) / 4)

    # Conservative output token estimate based on observed extraction outputs
    observed_out_tokens = len(triples) * 8 + len(entities) * 4
    scale = (len(new_chunks) / len(old_chunks)) if old_chunks else 1.0
    projected_out_tokens = round(observed_out_tokens * scale)

    graph_index_cost_observed = (old_in_tokens / 1_000_000) * CHAT_IN_PER_M + (
        observed_out_tokens / 1_000_000
    ) * CHAT_OUT_PER_M
    graph_index_cost_projected = (new_in_tokens / 1_000_000) * CHAT_IN_PER_M + (
        projected_out_tokens / 1_000_000
    ) * CHAT_OUT_PER_M

    flat_query_cost = sum(float(r["estimated_cost"]) for r in bench if r["system"] == "flat")
    graph_query_cost = sum(float(r["estimated_cost"]) for r in bench if r["system"] == "graph")

    flat_index_tokens = round(sum(len(r.get("text", "")) for r in corpus) / 4)
    flat_index_cost = (flat_index_tokens / 1_000_000) * EMBED_PER_M

    total_flat = flat_query_cost + flat_index_cost
    total_graph_observed = graph_query_cost + graph_index_cost_observed
    total_graph_projected = graph_query_cost + graph_index_cost_projected

    md = []
    md.append("# Cost Audit (Reality Check)")
    md.append("")
    md.append("## 1) Query-Time Cost (from benchmark)")
    md.append(f"- Flat query cost / 20Q: **${flat_query_cost:.4f}**")
    md.append(f"- Graph query cost / 20Q: **${graph_query_cost:.4f}**")
    md.append("- At query time only, Graph can be cheaper because graph context is shorter.")
    md.append("")
    md.append("## 2) Indexing Cost (where GraphRAG is usually more expensive)")
    md.append(f"- Flat indexing (embedding assumption): **${flat_index_cost:.4f}**")
    md.append(f"- Graph indexing (observed old chunking): **${graph_index_cost_observed:.4f}**")
    md.append(f"- Graph indexing (projected with fixed chunking): **${graph_index_cost_projected:.4f}**")
    md.append("")
    md.append("## 3) Total Cost View (Query + Indexing)")
    md.append(f"- Flat total (estimated): **${total_flat:.4f}**")
    md.append(f"- Graph total (old chunking): **${total_graph_observed:.4f}**")
    md.append(f"- Graph total (fixed chunking projection): **${total_graph_projected:.4f}**")
    md.append("")
    md.append("## 4) Why previous graph cost looked too low")
    md.append("- Old extraction chunking truncated long paragraphs, often to one chunk/article.")
    md.append(f"- Old extracted chunks: **{len(old_chunks)}**")
    md.append(f"- New extracted chunks (same max 2/article): **{len(new_chunks)}**")
    md.append(f"- Old input token estimate: **{old_in_tokens}**")
    md.append(f"- New input token estimate: **{new_in_tokens}**")
    md.append("")
    md.append("## 5) Conclusion")
    md.append("- If you include indexing, GraphRAG cost moves up substantially.")
    md.append("- For strict apples-to-apples: rerun extraction with fixed chunking, then rerun benchmark.")

    OUT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"[Done] {OUT_PATH}")


if __name__ == "__main__":
    main()
