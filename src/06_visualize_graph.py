import argparse
from pathlib import Path
import re

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
    parser.add_argument("--output", default=str(PNG_PATH))
    parser.add_argument("--evidence-edges", type=int, default=25)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    graph = load_graph()
    ctx = build_graphrag_context(args.question, graph, max_hops=args.max_hops)
    seeds = set(ctx["seeds"])
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = OUTPUT_DIR / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

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

    evidence_edges = set()
    evidence_nodes = set()
    for line in ctx["context"].splitlines()[: args.evidence_edges]:
        m = re.match(r"^(.*?) -\[(.*?)\]-> (.*?) \(source: .*?\)$", line.strip())
        if not m:
            continue
        u = m.group(1).strip()
        rel = m.group(2).strip()
        v = m.group(3).strip()
        evidence_edges.add((u, v, rel))
        evidence_nodes.add(u)
        evidence_nodes.add(v)

    keep_nodes.update(evidence_nodes)
    if len(keep_nodes) > args.max_nodes:
        keep_nodes = set(list(keep_nodes)[: args.max_nodes])

    sub = graph.subgraph(keep_nodes).copy()
    pos = nx.spring_layout(sub, seed=42, k=0.7)

    plt.figure(figsize=(14, 10))
    node_colors = []
    for n in sub.nodes():
        if n in seeds:
            node_colors.append("#ef476f")
        elif n in evidence_nodes:
            node_colors.append("#ffd166")
        else:
            node_colors.append("#4c78a8")
    nx.draw_networkx_nodes(sub, pos, node_size=700, node_color=node_colors, alpha=0.9)
    normal_edges = []
    highlight_edges = []
    for u, v, data in sub.edges(data=True):
        rel = str(data.get("relation", ""))
        if (u, v, rel) in evidence_edges:
            highlight_edges.append((u, v))
        else:
            normal_edges.append((u, v))
    nx.draw_networkx_edges(sub, pos, edgelist=normal_edges, arrows=True, width=0.8, alpha=0.35, edge_color="#9aa0a6")
    nx.draw_networkx_edges(sub, pos, edgelist=highlight_edges, arrows=True, width=2.4, alpha=0.9, edge_color="#f77f00")
    nx.draw_networkx_labels(sub, pos, font_size=8)

    edge_labels = {}
    for u, v, data in sub.edges(data=True):
        rel = data.get("relation", "")
        if (u, v) not in edge_labels and rel:
            edge_labels[(u, v)] = rel
    nx.draw_networkx_edge_labels(sub, pos, edge_labels=edge_labels, font_size=7)

    plt.title("GraphRAG Subgraph (seed + evidence highlighted)", fontsize=14)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=220)
    print(f"[Done] Saved visualization: {output_path}")


if __name__ == "__main__":
    main()
