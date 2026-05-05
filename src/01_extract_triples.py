import argparse
import csv
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import quote_plus
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
COMPANY_LIST_PATH = DATA_DIR / "company_list.txt"
CORPUS_PATH = DATA_DIR / "corpus_articles.jsonl"
TRIPLES_PATH = OUTPUT_DIR / "triples.csv"
ENTITIES_PATH = OUTPUT_DIR / "entities.csv"

SYSTEM_PROMPT = """You extract structured knowledge graph data from text.
Return ONLY JSON:
{
  "entities": [{"name": "string", "type": "string"}],
  "relations": [{"subject": "string", "predicate": "string", "object": "string"}]
}
Rules:
- Use concise canonical entity names.
- Predicate format must be UPPER_SNAKE_CASE.
- Only include facts explicitly supported by the text.
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


def read_company_list(limit: int) -> List[str]:
    lines = COMPANY_LIST_PATH.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip()][:limit]


def fetch_wikipedia_article(title: str) -> Dict[str, str]:
    base = "https://en.wikipedia.org/w/api.php"
    params = (
        "action=query&format=json&prop=extracts&explaintext=1&redirects=1"
        f"&titles={quote_plus(title)}"
    )
    url = f"{base}?{params}"
    req = Request(
        url,
        headers={
            "User-Agent": "Day19GraphRAGBot/1.0 (student-lab; contact: local-project)",
            "Accept": "application/json",
        },
    )
    with urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    pages = payload.get("query", {}).get("pages", {})
    if not pages:
        return {}
    page = next(iter(pages.values()))
    if "missing" in page:
        return {}

    text = normalize_text(page.get("extract", ""))
    if not text:
        return {}

    page_title = page.get("title", title)
    wiki_url = f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
    return {"title": page_title, "url": wiki_url, "text": text}


def chunk_text(text: str, max_chars: int = 3200) -> List[str]:
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


def extract_from_chunk(client: OpenAI, chunk: str) -> Dict:
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
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--fetch-retries", type=int, default=5)
    parser.add_argument("--retry-base-sleep", type=float, default=2.0)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    companies = read_company_list(args.limit)

    print(f"[1/3] Fetching corpus from Wikipedia for {len(companies)} company pages...")
    corpus_rows: List[Dict] = []
    for idx, company in enumerate(companies, start=1):
        article = None
        for attempt in range(args.fetch_retries):
            try:
                article = fetch_wikipedia_article(company)
                break
            except HTTPError as exc:
                if exc.code == 429 and attempt < args.fetch_retries - 1:
                    wait_s = args.retry_base_sleep * (2 ** attempt)
                    print(f"  - [{idx}/{len(companies)}] 429 {company}, retry in {wait_s:.1f}s")
                    time.sleep(wait_s)
                    continue
                print(f"  - [{idx}/{len(companies)}] ERROR {company}: {exc}")
                break
            except Exception as exc:
                print(f"  - [{idx}/{len(companies)}] ERROR {company}: {exc}")
                break
        if not article:
            continue
        article["source_company"] = company
        corpus_rows.append(article)
        print(f"  - [{idx}/{len(companies)}] {article['title']}")
        time.sleep(args.sleep_seconds)

    write_jsonl(CORPUS_PATH, corpus_rows)
    print(f"[Saved] Corpus {len(corpus_rows)} -> {CORPUS_PATH}")

    print("[2/3] LLM extraction: entities + triples...")
    client = OpenAI(api_key=OPENAI_API_KEY)
    entity_name_by_key: Dict[str, str] = {}
    triples_set: set[Tuple[str, str, str, str]] = set()

    for article in corpus_rows:
        title = article["title"]
        chunks = chunk_text(article["text"])[: args.max_chunks_per_article]
        for chunk in chunks:
            try:
                result = extract_from_chunk(client, chunk)
            except Exception as exc:
                print(f"  - LLM error ({title}): {exc}")
                continue

            for ent in result.get("entities", []):
                name = normalize_text(str(ent.get("name", "")))
                if not name:
                    continue
                key = canonical_key(name)
                if key and key not in entity_name_by_key:
                    entity_name_by_key[key] = name

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
                if s_key not in entity_name_by_key:
                    entity_name_by_key[s_key] = subject
                if o_key not in entity_name_by_key:
                    entity_name_by_key[o_key] = obj
                triples_set.add((entity_name_by_key[s_key], predicate, entity_name_by_key[o_key], title))

    print("[3/3] Writing entities/triples...")
    with ENTITIES_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["entity_id", "name"])
        writer.writeheader()
        for key, name in sorted(entity_name_by_key.items(), key=lambda x: x[1].lower()):
            writer.writerow({"entity_id": key, "name": name})

    with TRIPLES_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["subject", "predicate", "object", "source_doc"])
        writer.writeheader()
        for s, p, o, doc in sorted(triples_set):
            writer.writerow({"subject": s, "predicate": p, "object": o, "source_doc": doc})

    print(f"[Done] {len(entity_name_by_key)} entities -> {ENTITIES_PATH}")
    print(f"[Done] {len(triples_set)} triples -> {TRIPLES_PATH}")


if __name__ == "__main__":
    main()
