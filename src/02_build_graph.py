import argparse
import csv
import pickle
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
TRIPLES_PATH = OUTPUT_DIR / "triples.csv"
GRAPH_PATH = OUTPUT_DIR / "graph.pkl"
GRAPH_STATS_PATH = OUTPUT_DIR / "graph_stats.txt"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--triples-path", default=str(TRIPLES_PATH))
    parser.add_argument("--graph-path", default=str(GRAPH_PATH))
    args = parser.parse_args()

    triples_path = Path(args.triples_path)
    graph_path = Path(args.graph_path)

    if not triples_path.exists():
        raise FileNotFoundError(f"Missing triples file: {triples_path}")

    graph = nx.MultiDiGraph()
    with triples_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            s = (row.get("subject") or "").strip()
            p = (row.get("predicate") or "").strip()
            o = (row.get("object") or "").strip()
            doc = (row.get("source_doc") or "").strip()
            if not s or not p or not o:
                continue
            graph.add_node(s)
            graph.add_node(o)
            graph.add_edge(s, o, relation=p, source_doc=doc)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with graph_path.open("wb") as f:
        pickle.dump(graph, f)

    degree_sorted = sorted(graph.degree, key=lambda x: x[1], reverse=True)[:20]
    lines = [
        f"nodes={graph.number_of_nodes()}",
        f"edges={graph.number_of_edges()}",
        "top_degree_nodes:",
    ]
    for node, deg in degree_sorted:
        lines.append(f"- {node}: {deg}")
    GRAPH_STATS_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"[Done] Graph saved: {graph_path}")
    print(f"[Done] nodes={graph.number_of_nodes()} edges={graph.number_of_edges()}")
    print(f"[Done] Stats: {GRAPH_STATS_PATH}")


if __name__ == "__main__":
    main()
