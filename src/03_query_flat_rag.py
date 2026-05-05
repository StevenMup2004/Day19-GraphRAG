import argparse
import json
from pathlib import Path

from rag_lib import answer_flat_rag

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
OUT_PATH = OUTPUT_DIR / "flat_last_answer.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result = answer_flat_rag(args.question)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(result["answer"])
    print(f"\nlatency_ms={result['latency_ms']}")
    print(f"token_in={result['token_in']} token_out={result['token_out']}")
    print(f"estimated_cost={result['estimated_cost']}")
    print(f"docs={result.get('documents', [])}")
    print(f"saved={OUT_PATH}")


if __name__ == "__main__":
    main()
