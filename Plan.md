# PLAN LAB DAY19 - GraphRAG 

## 0) Chot pham vi theo de bai

Lua chon cong cu:
- Chon `A - NetworkX` 

Yeu cau bat buoc can dat (doi chieu tu `INSTRUCTION.MD`):
- [ ] Corpus 100 bai Wikipedia ve AI companies.
- [ ] Entity + Relation extraction bang LLM -> sinh triples `(subject, predicate, object)`.
- [ ] Build graph bang `NetworkX`.
- [ ] Query pipeline theo dung logic: `question -> seed entities -> BFS 2-hop -> subgraph-to-text -> LLM answer`.
- [ ] Chay duoc 2 query mau:
  - [ ] `What is OpenAI?` (Flat RAG va GraphRAG deu tra loi dung).
  - [ ] `AI companies co-founded by former Google employees` (GraphRAG phai tot hon Flat RAG).
- [ ] Benchmark `20` cau hoi multi-hop: so sanh `accuracy, latency, cost`.
- [ ] Co visualization bang `NetworkX + matplotlib` (anh chup man hinh).
- [ ] Nop du 4 deliverables: code + screenshot + benchmark table + cost/time analysis.

Ghi chu quan trong:
- Trong noi dung huong dan co dong test 5 cau hoi phuc tap, nhung deliverable va muc tieu benchmark la 20 cau. De an toan cham diem: lam du `20` cau, co the danh dau 5 cau dau la bo "demo bat buoc".

## 1) Chuan hoa duong dan moi truong

Duong dan lam viec:
- Project: `C:\Users\dangv\Downloads\VinCourse\day19\Day19-GraphRAG`
- Virtual env bat buoc: `C:\Users\dangv\Downloads\VinCourse\day19\Day19-GraphRAG\.venv`
- File env dung chung: `C:\Users\dangv\Downloads\VinCourse\day19\.env`

Noi dung goi y cho `C:\Users\dangv\Downloads\VinCourse\day19\.env`:
```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

Nguyen tac:
- Khong commit `.env`.
- Tat ca script trong `Day19-GraphRAG` doc bien moi truong tu file `.env` o thu muc cha (duong dan tuong doi dung: `..\.env`, tuong ung `C:\Users\dangv\Downloads\VinCourse\day19\.env`).

Mau `src/config.py` (toi thieu):
```python
from pathlib import Path
from dotenv import load_dotenv
import os

ROOT = Path(__file__).resolve().parents[1]  # Day19-GraphRAG
ENV_PATH = ROOT.parent / ".env"             # day19/.env
load_dotenv(ENV_PATH)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

if not OPENAI_API_KEY:
    raise RuntimeError(f"Missing OPENAI_API_KEY in {ENV_PATH}")
```

## 2) Setup moi truong (PowerShell)

Chay tu PowerShell:
```powershell
Set-Location 'C:\Users\dangv\Downloads\VinCourse\day19\Day19-GraphRAG'

# Tao venv neu chua co
py -m venv .venv

# Kich hoat venv
.\.venv\Scripts\Activate.ps1

# Nang pip
python -m pip install --upgrade pip

# Cai thu vien cho NetworkX + Flat RAG baseline + LLM
pip install networkx matplotlib openai pandas python-dotenv langchain langchain-openai chromadb
```

Checklist setup:
- [ ] `python --version` chay trong `.venv`.
- [ ] `pip list` thay du cac goi tren.
- [ ] `C:\Users\dangv\Downloads\VinCourse\day19\.env` ton tai va co `OPENAI_API_KEY`.

## 3) Cau truc thu muc de lam nhanh

```text
Day19-GraphRAG/
  data/
    corpus_articles.json
    benchmark_questions.csv
  src/
    config.py
    01_extract_triples.py
    02_build_graph.py
    03_query_flat_rag.py
    04_query_graphrag.py
    05_benchmark.py
    06_visualize_graph.py
  outputs/
    triples.csv
    graph.pkl
    graph_context_samples.txt
    benchmark_results.csv
    graph_screenshot.png
    report.md
  Plan.md
```

## 4) Ke hoach code chi tiet (script-by-script)

### `src/config.py`
Muc tieu:
- Load env tu file tuyet doi: `C:\Users\dangv\Downloads\VinCourse\day19\.env`.
- Tra ve `OPENAI_API_KEY`, `OPENAI_MODEL`.

Kiem tra:
- [ ] Neu thieu key -> throw error ro rang.

### `src/01_extract_triples.py`
Muc tieu:
- Doc 100 article.
- Goi LLM de extract triples.
- Chuan hoa thuc the (dedup): lower/strip/punctuation cleanup + alias map.
- Ghi `outputs/triples.csv`.

Cot output goi y:
- `subject,predicate,object,source_doc`

Kiem tra:
- [ ] >= 300 triples hop le.
- [ ] Khong de predicate rong.

### `src/02_build_graph.py`
Muc tieu:
- Load `triples.csv` -> tao `networkx.MultiDiGraph()`.
- Them edge attrs: `relation`, `source_doc`.
- Luu graph: `outputs/graph.pkl`.

Kiem tra:
- [ ] In thong ke: so node, so edge, top degree nodes.

### `src/03_query_flat_rag.py`
Muc tieu:
- Baseline Flat RAG (vector retrieval text chunks, khong dung graph traversal).
- Dung cung model LLM nhu GraphRAG de so sanh cong bang.

Kiem tra:
- [ ] Tra ve answer + token usage + latency.

### `src/04_query_graphrag.py`
Muc tieu:
- Pipeline dung theo de:
  1. Entity extraction tu question.
  2. Map entity -> graph seed nodes.
  3. BFS depth=2 (co fallback depth=3 neu context qua it).
  4. Textualization subgraph (triples + path explanation).
  5. LLM answer "only from provided graph context".

Kiem tra:
- [ ] Query `What is OpenAI?` chay on.
- [ ] Query multi-hop ve former Google employees tra loi co path giai thich.

### `src/05_benchmark.py`
Muc tieu:
- Chay 20 cau hoi cho ca `Flat RAG` va `GraphRAG`.
- Scoring nhi phan `correct/incorrect` theo `ground_truth`.
- Ghi `outputs/benchmark_results.csv`.

Cot output goi y:
- `question_id,question,system,answer,correct,latency_ms,token_in,token_out,estimated_cost`

Kiem tra:
- [ ] Tong hop duoc accuracy trung binh.
- [ ] GraphRAG dat target uplift `>= 20%` so voi Flat RAG (neu chua dat, ghi failure analysis trung thuc).

### `src/06_visualize_graph.py`
Muc tieu:
- Ve subgraph lien quan den 1 query multi-hop.
- Highlight node/edge trong answer path.
- Luu `outputs/graph_screenshot.png`.

Kiem tra:
- [ ] Anh doc duoc labels chinh.

## 5) Lich 2 gio de chay lab

0:00-0:15
- Setup `.venv`, install libs, kiem tra `.env`.

0:15-0:45
- Extract triples + dedup.

0:45-1:05
- Build NetworkX graph + thong ke graph.

1:05-1:25
- Hoan thien GraphRAG query function (BFS + textualization + answer).

1:25-1:40
- Hoan thien Flat RAG baseline.

1:40-1:55
- Chay benchmark 20 cau + xuat bang so sanh.

1:55-2:00
- Ve graph screenshot + viet `outputs/report.md`.

## 6) Mau benchmark table cho bao cao

| Metric | Flat RAG | GraphRAG | Delta |
|---|---:|---:|---:|
| Accuracy (20 Q) |  |  |  |
| Avg Latency (ms) |  |  |  |
| Avg Input Tokens |  |  |  |
| Avg Output Tokens |  |  |  |
| Estimated Cost / 20 Q |  |  |  |

Failure modes bat buoc viet ngan:
- Entity ambiguity.
- Missing relation chain.
- Hallucination khi context retrieval khong du.

## 7) Lenh chay nhanh cuoi cung

```powershell
Set-Location 'C:\Users\dangv\Downloads\VinCourse\day19\Day19-GraphRAG'
.\.venv\Scripts\Activate.ps1

python .\src\01_extract_triples.py
python .\src\02_build_graph.py
python .\src\03_query_flat_rag.py --question "What is OpenAI?"
python .\src\04_query_graphrag.py --question "AI companies co-founded by former Google employees"
python .\src\05_benchmark.py
python .\src\06_visualize_graph.py
```

## 8) Checklist nop bai (final gate)

- [ ] Co code (`.py` hoac `.ipynb`) chay duoc trong `.venv`.
- [ ] Co `graph_screenshot.png` (NetworkX).
- [ ] Co `benchmark_results.csv` va bang tong hop trong `report.md`.
- [ ] Co phan tich cost/time.
- [ ] Co minh hoa ro truong hop Flat RAG sai nhung GraphRAG dung.
