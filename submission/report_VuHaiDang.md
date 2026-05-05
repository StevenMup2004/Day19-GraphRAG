# Báo Cáo Benchmark GraphRAG

**Name**: Vu Hai Dang - 2A202600339


| Chỉ số | Flat RAG | GraphRAG | Chênh lệch |
|---|---:|---:|---:|
| Độ chính xác (20 câu) | 60.00% | 90.00% | 30.00% |
| Độ trễ trung bình (ms) | 1305.7 | 1154.3 | -151.4 |
| Số token input trung bình | 2186.2 | 1041.4 | -1144.8 |
| Số token output trung bình | 22.4 | 22.7 | 0.3 |
| Tổng chi phí ước tính (Query + Indexing, USD) | 0.0119 | 0.0176 | +0.0057 |

## Đánh Giá Trên Repository (Accuracy, Latency, Cost)
- Phạm vi: đánh giá trên repository này với 20 câu benchmark và 2 hệ thống (`flat`, `graph`).
- Độ chính xác: GraphRAG cao hơn Flat RAG **+30.00% tuyệt đối** (90% so với 60%).
- Độ trễ: GraphRAG nhanh hơn khoảng **151 ms/câu hỏi** trung bình.
- Chi phí lúc truy vấn: GraphRAG thấp hơn khoảng **$0.0034 / 20 câu hỏi**.
- Tổng chi phí (query + indexing): GraphRAG cao hơn khoảng **$0.0057**.

### Đối Chiếu Chi Phí Thực Tế (Query + Indexing)
- Nếu chỉ nhìn query-time benchmark, GraphRAG có thể trông rẻ hơn.
- Để phản ánh đầy đủ pipeline, cần cộng cả chi phí indexing/triple-extraction từ `outputs/cost_audit.md`:
- Flat tổng (query + indexing): **~$0.0119**
- Graph tổng (query + indexing, dự phóng với chunking đã sửa): **~$0.0176**
- Kết luận: GraphRAG cho chất lượng tốt hơn trên benchmark này, nhưng tổng chi phí đầy đủ cao hơn khi tính cả indexing.

## Giao Thức Chấm Điểm (Không Mock)
- Chấm theo từ khóa xác định (deterministic): `expected_keywords` được parse theo AND-of-OR groups.
- Mọi câu trả lời dạng từ chối (`cannot answer`, `insufficient`, ...) đều bị chấm sai.
- Flat RAG và GraphRAG dùng cùng một logic chấm điểm.

## Phân Tích Failure Modes
- Thiếu cạnh quan trọng cho câu hỏi factoid đơn giản:
- Ví dụ: `FQ19` (Ai sáng lập OpenAI?) và `FQ20` (OpenAI thành lập năm nào?) khi GraphRAG trả về thiếu ngữ cảnh.
- Nguyên nhân gốc: seed/entity match + BFS giới hạn số hop không kéo được relation founder/year vào subgraph context.
- Mơ hồ thực thể và lệch alias:
- Cùng một thực thể ngoài đời có thể xuất hiện dưới nhiều tên khác nhau, làm giảm độ chính xác của seed và suy yếu recall của BFS.
- Thiếu bao phủ ở bước trích xuất relation:
- Nếu extraction bỏ sót relation chain quan trọng, graph traversal không thể tự khôi phục dù chọn seed đúng.
- Cơ chế trả lời quá chặt:
- Prompt policy "chỉ trả lời từ context" giúp giảm hallucination, nhưng làm tăng số câu từ chối khi retrieval thiếu dữ kiện.

### Giải Thích Chi Tiết Cho `robustness_failcase` (FQ19, FQ20)
1. Lệch alias ở mức graph node:
- Trong graph đang tồn tại node tách rời như `OpenAI` và `OpenAI Global, LLC`.
- Fact `FOUNDED_IN 2015` lại gắn với `OpenAI Global, LLC`, trong khi truy vấn thường match vào `OpenAI`.

2. Thiếu relation founder trong triples:
- Trong `outputs/triples.csv` hiện tại có `FOUNDED_IN`, nhưng `FOUNDED_BY` chưa ổn định trên cùng node liên quan OpenAI.
- Vì vậy câu hỏi `Ai sáng lập OpenAI?` không có cạnh trực tiếp để trả lời từ graph.

3. Giới hạn retrieval và traversal:
- Bước chọn seed + BFS giới hạn hop có thể bỏ lỡ node chứa fact founder/year cần thiết.
- Khi node/cạnh đó không vào subgraph context, bước sinh câu trả lời sẽ không có bằng chứng để trả lời.

4. Prompt strict khiến lỗi retrieval thành lỗi chấm điểm:
- Prompt QA ép model "chỉ trả lời từ context đã cấp".
- Khi thiếu evidence, model sẽ từ chối hợp lệ (`insufficient context`), nhưng benchmark vẫn chấm sai.
