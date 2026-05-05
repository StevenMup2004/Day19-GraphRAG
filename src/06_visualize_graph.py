import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

from rag_lib import build_graphrag_context, load_graph

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
PNG_PATH = OUTPUT_DIR / "graph_screenshot.png"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--question",
        default="AI companies co-founded by former Google employees",
    )
    parser.add_argument("--max-hops", type=int, default=2)
    parser.add_argument("--max-nodes", type=int, default=50)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    graph = load_graph()
    ctx = build_graphrag_context(args.question, graph, max_hops=args.max_hops)
    seeds = set(ctx["seeds"])

    undirected = graph.to_undirected()
    keep_nodes = set()
    for s in seeds:
        if s in undirected:
            lengths = nx.single_source_shortest_path_length(undirected, s, cutoff=args.max_hops)
            keep_nodes.update(lengths.keys())
    if not keep_nodes:
        keep_nodes = set(list(graph.nodes())[: args.max_nodes])
    if len(keep_nodes) > args.max_nodes:
        keep_nodes = set(list(keep_nodes)[: args.max_nodes])

    sub = graph.subgraph(keep_nodes).copy()
    pos = nx.spring_layout(sub, seed=42, k=0.8)

    plt.figure(figsize=(14, 10))
    node_colors = ["#ff6b6b" if n in seeds else "#4c78a8" for n in sub.nodes()]
    nx.draw_networkx_nodes(sub, pos, node_size=700, node_color=node_colors, alpha=0.9)
    nx.draw_networkx_edges(sub, pos, arrows=True, width=1.0, alpha=0.5, edge_color="#888")
    nx.draw_networkx_labels(sub, pos, font_size=8)

    edge_labels = {}
    for u, v, data in sub.edges(data=True):
        rel = data.get("relation", "")
        if (u, v) not in edge_labels and rel:
            edge_labels[(u, v)] = rel
    nx.draw_networkx_edge_labels(sub, pos, edge_labels=edge_labels, font_size=7)

    plt.title("GraphRAG Subgraph (seed nodes highlighted)", fontsize=14)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(PNG_PATH, dpi=200)
    print(f"[Done] Saved visualization: {PNG_PATH}")


if __name__ == "__main__":
    main()
