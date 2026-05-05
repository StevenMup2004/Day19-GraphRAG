LAB DAY 19: XÂY DỰNG HỆ THỐNG GRAPHRAG VỚI TECH COMPANY CORPUS 



GraphRAG trên Tech Company Corpus
1. Corpus: 100 Wikipedia articles AI companies, extract entities → Neo4j graph
2. Query 1 (flat RAG OK): "What is OpenAI?" cả hai pipeline đúng
3. Query 2 (multi-hop): "AI companies co-founded by former Google employees" flat RAG hallucinate, GraphRAG đúng
4. Visualization: Neo4j Browser hiển thị subgraph, highlight answer nodes

Mục tiêu: Build Knowledge Graph + GraphRAG agent, multi-hop accuracy vượt flat RAG + 20%
Deliverable: Knowledge graph visualization + GraphRAG benchmark report (multi-hop accuracy, latency, cost)
Thời gian: 2 giờ

Lab 19 - Các bước thực hành
1. Entity extraction: Dùng LLM-based NER trên domain corpus, output triples (subject, predicate, object)
2. Build graph: Load triples vào NetworkX (hoặc Neo4j), thêm embeddings cho nodes
3. GraphRAG retrieval: Implement query → seed nodes → BFS traversal → subgraph-to-text → LLM generate
VINUNIVERSITY
4. Benchmark: So sánh GraphRAG vs Flat RAG trên 20 multi-hop questions đo accuracy, latency, cost
GitHub repo + Neo4j/NetworkX visualization + benchmark report: bảng accuracy, phân tích failure modes

1. MỤC TIÊU BÀI HỌC
Hiểu rõ quy trình trích xuất thực thể (Entity Extraction) và quan hệ (Relation Extraction) từ văn bản thô.
Làm quen với các thư viện quản lý đô thị: NetworkX, Neo4j và framework mã nguồn mở NodeRAG.
Xây dựng hoàn chỉnh một pipeline GraphRAG: từ lập chỉ mục (Indexing) đến truy vấn đa bước (Multi-hop Querying).
Đánh giá sự khác biệt về độ chính xác giữa Flat RAG và GraphRAG.


2. PHẦN 1: NGHIÊN CỨU VÀ CHUẨN BỊ (RESEARCH)
Trước khi bắt đầu code, sinh viên cần tìm hiểu các khái niệm và công cụ sau:
2.1. Quy trình xử lý dữ liệu đồ thị
Sinh viên cần trả lời được các câu hỏi:
1. Entity Extraction: Làm sao để LLM phân biệt được đâu là thực thế (Node) và đâu là thuộc tính?
2. Graph Construction: Tại sao việc khử trùng lặp (Deduplication) lại quan trọng trong đô thị?
3. Query Answering: Sự khác biệt giữa duyệt đồ thị theo chiều rộng (BFS) và tìm kiếm vector thông thường là gì?


2.2. Tìm hiểu công cụ
NetworkX: Thư viện Python dùng để nghiên cứu các mạng lưới phức tạp. Phù hợp cho việc tạo prototype nhanh.
Neo4j: Cơ sở dữ liệu đồ thị chuẩn công nghiệp, sử dụng ngôn ngữ truy vấn Cypher.
NodeRAG: Một framework mã nguồn mở xây dựng trên nën NetworkX, giúp đơn giản hóa việc tích hợp GraphRAG vào ứng dụng Python. 3. PHẦN 2: ENVIRONMENT SETUP
Mở terminal hoặc command prompt và cài đặt các thư viện cần thiết:


Bash
# Cài đặt các thư viện cơ bản cho xử lý ngôn ngữ và đồ thị 
pip install networkx matplotlib neo4j openai pandas
# Cài đặt NodeRAG framework
pip install noderag
# Nêu sử dụng LangChain để hỗ trợ pipeline
pip install langchain langchain-openai
Lưu ý: Đối với Neo4j, sinh viên nên sử dụng Neo4j Desktop hoặc chạy qua Docker để có giao diện trực quan hóa (Bloom/Browser).



4. PHẦN 3: HƯỚNG DẪN THỰC HIỆN TỪNG BƯỚC
Bước 1: Trích xuất thực thể và quan hệ (Indexing)
Sử dụng LLM để đọc bộ dữ liệu "Tech Company Corpus" và chuyến đối thành các bộ ba (Triples).
Input: "OpenAI được thành lập bởi Sam Altman và Elon Musk vào năm 2015."
Output (Triples):
(OpenAI, FOUNDED_BY, Sam Altman)
(OpenAI, FOUNDED_BY, Elon Musk)
(OpenAI, FOUNDED_IN, 2015)


Bước 2: Xây dựng đồ thị (Construction)
Sinh viên thực hiện đấy dữ liệu vào một trong ba công cụ sau:
Lựa chọn A (NetworkX): Phù hợp để chạy offline trong Notebook.
Lựa chọn B (Neo4j): Khuyên dùng nếu muốn trực quan hóa các mối liên kết bằng mắt thường.
Lựa chọn C (NodeRAG): Sử dụng nếu muốn một giải pháp trọn gói (all-in-one) đã được tối ưu sẵn logic tìm kiếm. 


Bước 3: Thực thi truy vấn (Querying)
Viết hàm xử lý truy vấn theo logic:
1. Nhận câu hỏi từ người dùng.
2. Trích xuất thực thế chính trong câu hỏi (ví dụ: "Google").
3. Tìm node tương ứng trong đô thị và duyệt (traverse) các node lân cận trong phạm vi 2-hop.
4. Gộp các thông tin tìm được thành một đoạn văn (Textualization) và gửi cho LLM.


Bước 4: So sánh và Đánh giá (Evaluation)
Sinh viên chạy thử 5 câu hỏi phức tạp trên cả hai hệ thống:
1. Flat RAG: Chỉ dùng ChromaDB/Faiss.
2. GraphRAG: Dùng đồ thị vừa xây dựng.
Yêu cầu: Ghi lại các trường hợp Flat RAG bị ảo giác nhưng GraphRAG trả lời đúng.



5. ĐỀ XUẤT CÔNG CỤ (RECOMMENDATIONS)
Mục tiêu  Dễ bắt đầu  Tool gợi ý  NodeRAG
Lý do: Tích hợp sẵn logic GraphRAG, không cần cấu hình database phức tạp
Trực quan hóa tốt nhất
Neo4j
Giao diện đồ họa giúp"thấy" được tri thức đang được kết nối như thế nào.
Nghiên cứu thuật toán
NetworkX
Cho phép can thiệp sâu vào các thuật toán toán học của đồ thị.

 6. DELIVERABLES
Sinh viên nộp báo cáo bao gồm:
1. Mã nguồn (File.py hoặc .ipynb).
2. Ảnh chụp màn hình đô thị tri thức đã xây dựng (từ Neo4j hoặc Matplotlib).
3. Bảng so sánh kết quả 20 câu hỏi benchmark giữa Flat RAG và GraphRAG.
4. Phân tích ngắn gọn về chi phí (Token usage, time) khi xây dựng đô thị.