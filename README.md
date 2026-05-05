# Day19-GraphRAG

Mini project GraphRAG cho miền AI companies:
- Thu thập corpus từ Wikipedia
- Trích xuất entity/relation bằng LLM thành triples `(subject, predicate, object)`
- Xây dựng graph bằng `NetworkX`
- So sánh `Flat RAG` và `GraphRAG` theo `accuracy`, `latency`, `cost`

## 1) Cấu Trúc Project

```text
Day19-GraphRAG/
  data/
    company_list.txt
    corpus_articles.jsonl
    benchmark_questions*.csv
  outputs/
    entities.csv
    triples.csv
    graph.pkl
    graph_stats.txt
    benchmark_results_final.csv
    report_final.md
    cost_audit.md
    graph_screenshot_final.png
  src/
    config.py
    01_extract_triples.py
    02_build_graph.py
    03_query_flat_rag.py
    04_query_graphrag.py
    05_benchmark.py
    06_visualize_graph.py
    07_analyze_report.py
    08_cost_audit.py
```

## 2) Cài Đặt Môi Trường

Yêu cầu:
- Python 3.10+
- OpenAI API key

Tạo file `.env` tại thư mục cha `day19/.env`:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

Cài đặt:

```powershell
Set-Location 'C:\Users\dangv\Downloads\VinCourse\day19\Day19-GraphRAG'
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install networkx matplotlib openai pandas python-dotenv
```

## 3) Chạy Pipeline End-to-End

```powershell
.\.venv\Scripts\Activate.ps1

python .\src\01_extract_triples.py --limit 100
python .\src\02_build_graph.py

python .\src\03_query_flat_rag.py --question "What is OpenAI?"
python .\src\04_query_graphrag.py --question "AI companies co-founded by former Google employees"

python .\src\05_benchmark.py --questions-path .\data\benchmark_questions_final.csv
python .\src\06_visualize_graph.py --output graph_screenshot_final.png

python .\src\07_analyze_report.py --results .\outputs\benchmark_results_final.csv --questions .\data\benchmark_questions_strict.csv --output .\outputs\report_detailed_final.md
python .\src\08_cost_audit.py
```

## 4) Logic Pipeline Chính

GraphRAG:
1. Trích xuất seed entities từ câu hỏi
2. Ánh xạ vào graph nodes
3. Mở rộng BFS theo `max_hops` (mặc định 2)
4. Chuyển các cạnh trong subgraph thành context text
5. Gọi LLM trả lời chỉ dựa trên graph context

Flat RAG baseline:
1. Lexical retrieve top documents từ corpus
2. Gửi text context vào cùng model LLM
3. So sánh đầu ra với cùng logic chấm điểm

## 5) Kết Quả Đầu Ra

- `outputs/triples.csv`: triples được trích xuất bởi LLM
- `outputs/graph.pkl`: graph `NetworkX MultiDiGraph` đã serialize
- `outputs/benchmark_results_final.csv`: chi tiết benchmark theo từng dòng
- `outputs/report_final.md`: báo cáo tổng hợp tiếng Việt (accuracy, latency, cost, failure modes)
- `outputs/cost_audit.md`: chi phí query so với chi phí đầy đủ (query + indexing)
- `outputs/graph_screenshot_final.png`: ảnh visualization

## 6) submission

Đã có sẵn thư mục gom report + ảnh để nộp nhanh:

- `submission/report_VuHaiDang.md`
- `submission/graph_screenshot_VuHaiDang.png`

## 7) Ghi Chú Đánh Giá

- Accuracy trong report được tính trên 20 câu hỏi.
- Query-time cost có thể thấp hơn cho GraphRAG do context gọn hơn.
- Total cost (query + indexing) thường cao hơn cho GraphRAG vì có chi phí extraction + graph indexing.
- Cách chấm hiện tại là keyword-based deterministic scoring, chưa phải semantic grader.

## 8) Failure Modes Thường Gặp

- Lệch alias entity (ví dụ `OpenAI` và `OpenAI Global, LLC`)
- Thiếu relation quan trọng (ví dụ thiếu `FOUNDED_BY`)
- Traversal giới hạn số hop nên có thể bỏ sót evidence node
- Prompt policy quá chặt có thể tạo câu trả lời từ chối khi context retrieval thiếu

## 9) Troubleshooting Nhanh

- Lỗi `Missing OPENAI_API_KEY`: kiểm tra `day19/.env`.
- Lỗi `Missing graph file`: chạy lại `02_build_graph.py`.
- GraphRAG trả lời `insufficient context`: kiểm tra triples và alias mapping, tăng `--max-hops` khi cần.
