import json
import pickle
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple

import networkx as nx
from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
CORPUS_PATH = DATA_DIR / "corpus_articles.jsonl"
TRIPLES_PATH = OUTPUT_DIR / "triples.csv"
GRAPH_PATH = OUTPUT_DIR / "graph.pkl"


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9][a-zA-Z0-9.-]+", (text or "").lower())


def estimate_cost_usd(token_in: int, token_out: int) -> float:
    # Approximate price for lightweight model. Adjust as needed.
    return round((token_in / 1_000_000) * 0.15 + (token_out / 1_000_000) * 0.60, 6)


def get_client() -> OpenAI:
    return OpenAI(api_key=OPENAI_API_KEY)


def load_corpus(path: Path = CORPUS_PATH) -> List[Dict]:
    if not path.exists():
        return []
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_graph(path: Path = GRAPH_PATH) -> nx.MultiDiGraph:
    if not path.exists():
        raise FileNotFoundError(f"Missing graph file: {path}")
    with path.open("rb") as f:
        graph = pickle.load(f)
    return graph


def llm_answer(question: str, context: str, mode: str) -> Dict:
    client = get_client()
    system_prompt = (
        "You are a factual QA assistant. "
        "Answer strictly from the provided context. "
        "If context is insufficient, say so clearly."
    )
    user_prompt = (
        f"Mode: {mode}\n\n"
        f"Question:\n{question}\n\n"
        f"Context:\n{context}\n\n"
        "Return concise answer and cite key entities from context."
    )
    start = time.perf_counter()
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    latency_ms = int((time.perf_counter() - start) * 1000)
    answer = resp.choices[0].message.content or ""
    usage = resp.usage
    token_in = int(getattr(usage, "prompt_tokens", 0) or 0)
    token_out = int(getattr(usage, "completion_tokens", 0) or 0)
    return {
        "answer": answer.strip(),
        "latency_ms": latency_ms,
        "token_in": token_in,
        "token_out": token_out,
        "estimated_cost": estimate_cost_usd(token_in, token_out),
    }


def retrieve_flat_context(question: str, top_k: int = 4, max_chars: int = 12000) -> Dict:
    corpus = load_corpus()
    q_tokens = set(tokenize(question))
    scored: List[Tuple[int, Dict]] = []
    for row in corpus:
        text = row.get("text", "")
        tokens = set(tokenize(text))
        score = len(q_tokens.intersection(tokens))
        scored.append((score, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [row for score, row in scored[:top_k] if score > 0]
    if not selected:
        selected = [row for _, row in scored[:top_k]]

    chunks: List[str] = []
    for row in selected:
        title = row.get("title", "Unknown")
        text = row.get("text", "")[:2500]
        chunks.append(f"[{title}]\n{text}")
    context = "\n\n".join(chunks)
    return {"context": context[:max_chars], "documents": [r.get("title", "") for r in selected]}


def answer_flat_rag(question: str) -> Dict:
    retrieval = retrieve_flat_context(question)
    result = llm_answer(question, retrieval["context"], mode="flat_rag")
    result["documents"] = retrieval["documents"]
    return result


def find_seed_nodes(question: str, graph: nx.MultiDiGraph, limit: int = 8) -> List[str]:
    question_l = question.lower()
    nodes = [str(n) for n in graph.nodes]
    generic = {
        "company",
        "companies",
        "model",
        "models",
        "employee",
        "employees",
        "founder",
        "founders",
        "gpu",
        "gpus",
        "ai",
    }

    # strict exact phrase match first
    direct = []
    for n in nodes:
        nl = n.lower().strip()
        if len(nl) < 3 or nl in generic:
            continue
        if nl in question_l:
            direct.append(n)
    if direct:
        # prefer more specific, longer entities first
        return sorted(set(direct), key=len, reverse=True)[:limit]

    # controlled keyword match as fallback
    q_tokens = [t for t in tokenize(question) if len(t) >= 4 and t not in generic]
    scored: List[Tuple[int, int, str]] = []
    for n in nodes:
        nl = n.lower()
        hit = 0
        for tok in q_tokens:
            if re.search(rf"\b{re.escape(tok)}\b", nl):
                hit += 1
        if hit > 0:
            scored.append((hit, -len(n), n))

    scored.sort(reverse=True)
    return [n for _, _, n in scored[:limit]]


def build_graphrag_context(
    question: str,
    graph: nx.MultiDiGraph,
    max_hops: int = 2,
    max_edges: int = 120,
    max_chars: int = 12000,
) -> Dict:
    seeds = find_seed_nodes(question, graph)
    if not seeds:
        # fallback with high-degree nodes to avoid empty context
        deg_sorted = sorted(graph.degree, key=lambda x: x[1], reverse=True)
        seeds = [n for n, _ in deg_sorted[:3]]

    undirected = graph.to_undirected()
    keep_nodes = set(seeds)
    for seed in seeds:
        lengths = nx.single_source_shortest_path_length(undirected, seed, cutoff=max_hops)
        keep_nodes.update(lengths.keys())

    lines: List[str] = []
    edge_count = 0
    for u, v, data in graph.edges(data=True):
        if u in keep_nodes and v in keep_nodes:
            rel = str(data.get("relation", "RELATED_TO"))
            doc = str(data.get("source_doc", ""))
            lines.append(f"{u} -[{rel}]-> {v} (source: {doc})")
            edge_count += 1
            if edge_count >= max_edges:
                break

    context = "\n".join(lines)
    if not context:
        context = "No graph edges found for this query."
    return {"context": context[:max_chars], "seeds": seeds, "node_count": len(keep_nodes)}


def answer_graphrag(question: str, max_hops: int = 2) -> Dict:
    graph = load_graph()
    ctx = build_graphrag_context(question, graph, max_hops=max_hops)
    result = llm_answer(question, ctx["context"], mode="graph_rag")
    result["seed_nodes"] = ctx["seeds"]
    result["subgraph_nodes"] = ctx["node_count"]
    result["context_preview"] = ctx["context"][:1200]
    return result
