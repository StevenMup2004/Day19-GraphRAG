import argparse
import json
from pathlib import Path

from rag_lib import answer_graphrag

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
OUT_PATH = OUTPUT_DIR / "graphrag_last_answer.json"
CONTEXT_PATH = OUTPUT_DIR / "graph_context_samples.txt"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True)
    parser.add_argument("--max-hops", type=int, default=2)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result = answer_graphrag(args.question, max_hops=args.max_hops)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    CONTEXT_PATH.write_text(result.get("context_preview", ""), encoding="utf-8")

    print(result["answer"])
    print(f"\nlatency_ms={result['latency_ms']}")
    print(f"token_in={result['token_in']} token_out={result['token_out']}")
    print(f"estimated_cost={result['estimated_cost']}")
    print(f"seed_nodes={result.get('seed_nodes', [])}")
    print(f"subgraph_nodes={result.get('subgraph_nodes', 0)}")
    print(f"saved={OUT_PATH}")


if __name__ == "__main__":
    main()
