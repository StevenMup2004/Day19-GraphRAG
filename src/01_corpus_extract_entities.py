import argparse
import csv
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import quote_plus
from urllib.request import urlopen

from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
CORPUS_PATH = DATA_DIR / "corpus_articles.jsonl"
COMPANY_LIST_PATH = DATA_DIR / "company_list.txt"

SYSTEM_PROMPT = """You extract knowledge graph data from text.
Return ONLY JSON with this schema:
{
  "entities": [{"name": "string", "type": "string"}],
  "relations": [{"subject": "string", "predicate": "string", "object": "string"}]
}
Rules:
- Keep entities short and canonical.
- Predicates must be uppercase snake_case (e.g., FOUNDED_BY, HEADQUARTERED_IN).
- Only return facts grounded in the input text.
"""


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def canonical_key(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\s.-]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_predicate(s: str) -> str:
    s = s.strip().upper()
    s = re.sub(r"[^A-Z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def read_company_list(path: Path, limit: int) -> List[str]:
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()]
    names = [ln for ln in lines if ln]
    return names[:limit]


def fetch_wikipedia_article(title: str) -> Dict[str, str]:
    base = "https://en.wikipedia.org/w/api.php"
    params = (
        "action=query&format=json&prop=extracts&explaintext=1&redirects=1"
        f"&titles={quote_plus(title)}"
    )
    url = f"{base}?{params}"
    with urlopen(url, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    pages = payload.get("query", {}).get("pages", {})
    if not pages:
        return {}
    page = next(iter(pages.values()))
    if "missing" in page:
        return {}

    page_title = page.get("title", title)
    text = normalize_text(page.get("extract", ""))
    if not text:
        return {}

    wiki_url = f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
    return {"title": page_title, "url": wiki_url, "text": text}


def chunk_text(text: str, max_chars: int = 3500) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: List[str] = []
    cur: List[str] = []
    cur_len = 0

    for p in paragraphs:
        if len(p) > max_chars:
            p = p[:max_chars]
        if cur_len + len(p) + 1 > max_chars and cur:
            chunks.append("\n".join(cur))
            cur = [p]
            cur_len = len(p)
        else:
            cur.append(p)
            cur_len += len(p) + 1
    if cur:
        chunks.append("\n".join(cur))
    return chunks


def extract_chunk(client: OpenAI, chunk: str) -> Dict:
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": chunk},
        ],
    )
    content = resp.choices[0].message.content or "{}"
    return json.loads(content)


def write_jsonl(path: Path, rows: List[Dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--max-chunks-per-article", type=int, default=3)
    parser.add_argument("--sleep-seconds", type=float, default=0.5)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    companies = read_company_list(COMPANY_LIST_PATH, args.limit)
    print(f"[1/3] Fetching Wikipedia pages for {len(companies)} companies...")

    corpus_rows: List[Dict] = []
    for idx, company in enumerate(companies, start=1):
        try:
            article = fetch_wikipedia_article(company)
            if not article:
                print(f"  - Skip (not found): {company}")
                continue
            article["source_company"] = company
            corpus_rows.append(article)
            print(f"  - [{idx}/{len(companies)}] OK: {article['title']}")
            time.sleep(args.sleep_seconds)
        except Exception as exc:
            print(f"  - [{idx}/{len(companies)}] ERROR {company}: {exc}")

    write_jsonl(CORPUS_PATH, corpus_rows)
    print(f"[Saved] {CORPUS_PATH} ({len(corpus_rows)} articles)")

    print("[2/3] Extracting entities + triples with LLM...")
    client = OpenAI(api_key=OPENAI_API_KEY)

    entity_label_by_key: Dict[str, str] = {}
    triples_set: set[Tuple[str, str, str, str]] = set()

    for article in corpus_rows:
        title = article["title"]
        chunks = chunk_text(article["text"])[: args.max_chunks_per_article]
        for chunk in chunks:
            try:
                result = extract_chunk(client, chunk)
            except Exception as exc:
                print(f"  - LLM error on {title}: {exc}")
                continue

            for ent in result.get("entities", []):
                name = normalize_text(str(ent.get("name", "")))
                if not name:
                    continue
                key = canonical_key(name)
                if key and key not in entity_label_by_key:
                    entity_label_by_key[key] = name

            for rel in result.get("relations", []):
                subject = normalize_text(str(rel.get("subject", "")))
                predicate = normalize_predicate(str(rel.get("predicate", "")))
                obj = normalize_text(str(rel.get("object", "")))
                if not subject or not predicate or not obj:
                    continue

                s_key = canonical_key(subject)
                o_key = canonical_key(obj)
                if not s_key or not o_key:
                    continue
                if s_key not in entity_label_by_key:
                    entity_label_by_key[s_key] = subject
                if o_key not in entity_label_by_key:
                    entity_label_by_key[o_key] = obj

                triples_set.add(
                    (entity_label_by_key[s_key], predicate, entity_label_by_key[o_key], title)
                )

    print("[3/3] Writing outputs...")
    entities_path = OUTPUT_DIR / "entities.csv"
    triples_path = OUTPUT_DIR / "triples.csv"

    with entities_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["entity_id", "name"])
        writer.writeheader()
        for key, name in sorted(entity_label_by_key.items(), key=lambda x: x[1].lower()):
            writer.writerow({"entity_id": key, "name": name})

    with triples_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["subject", "predicate", "object", "source_doc"])
        writer.writeheader()
        for s, p, o, doc in sorted(triples_set):
            writer.writerow({"subject": s, "predicate": p, "object": o, "source_doc": doc})

    print(f"[Done] Entities: {len(entity_label_by_key)} -> {entities_path}")
    print(f"[Done] Triples: {len(triples_set)} -> {triples_path}")


if __name__ == "__main__":
    main()
