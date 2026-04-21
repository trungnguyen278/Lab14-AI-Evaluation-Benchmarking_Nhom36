# Individual Reflection — Huy Tú

> GitHub: huytu0702 · Email: tufy2k4@gmail.com

## 1. Vai trò trong nhóm & đóng góp cụ thể
- **Vai trò:** AI/Backend — chủ 2 phiên bản RAG Agent (V1 baseline + V2 optimized).
- **Module phụ trách:**
  - `agent/rag_agent_v1.py` — baseline version: `top_k=2`, generic prompt, không rerank/filter. Dùng raw ChromaDB `_collection.query()` để lấy ID thật (`doc_0`–`doc_29`) thay vì LangChain wrapper (vốn không expose ID).
  - `agent/rag_agent_v2.py` — optimized: `top_k=5`, query expansion (LLM rewrite ra 2 variant), relevance filtering với `score_threshold=0.3`, system prompt chi tiết có quy tắc "không bịa", trích dẫn nguồn.
  - `agent/main_agent.py` — Factory wrapper cho phép `MainAgent(version="v1"|"v2")`.
  - `agent/AGENT_OUTPUT_SAMPLE.md` — tài liệu sơ đồ Chunk ID + JSON output sample của V1 vs V2.
- **Số commit:** 4 (c716e95 init data, 36f839d ignore venv, ea5c0ac MainAgent factory, d97b4ec OpenAI embeddings).

## 2. Technical Depth — 3 khái niệm cốt lõi

### 2.1 MRR (Mean Reciprocal Rank)
- **Định nghĩa:** Trung bình của `1/rank` vị trí đầu tiên doc đúng xuất hiện trong retrieved list. Nếu không thấy, rank = ∞ → 1/rank = 0.
- **Trong lab:** V1 MRR = 0.92; V2 MRR = 0.935. Sự tăng nhỏ này xuất phát từ **query expansion** của V2: 2 biến thể câu hỏi giúp kéo chunk đúng lên vị trí 1 trong nhiều case mà V1 chỉ đưa lên vị trí 2.
- **MRR vs Hit Rate:** MRR nhạy với thứ hạng; Hit Rate @ k chỉ nhạy với sự hiện diện trong top-k. V1 và V2 cùng Hit Rate 0.98 nhưng MRR khác → V2 "xếp hạng" tốt hơn dù cùng tỉ lệ tìm thấy.

### 2.2 Cohen's Kappa / Multi-Judge
- **Kappa:** Hệ số đo đồng thuận loại trừ may rủi — nếu 2 judge ngẫu nhiên cùng cho 5 chỉ vì "đa số câu đều 5", Kappa vẫn thấp. Chỉ `agreement_rate = 1 − |A − B| / 4` có thể che giấu điều này.
- **Trong lab:** `kappa_like = 0.907` — có thể hơi cao vì phân phối điểm lệch mạnh về phía 5 (V2 có 48/50 pass) → cần nhiều case khó hơn để Kappa phản ánh đúng.

### 2.3 Position Bias
- **Định nghĩa:** Bias do thứ tự trình bày; LLM judge có xu hướng ưu tiên answer được trình bày trước.
- **Liên hệ với Agent của mình:** Bản thân agent V2 có "source citation" `(Nguồn: policy_refund_v4.txt)` ở cuối câu trả lời — nếu Judge quét đoạn cuối để xác thực, vị trí của citation có thể ảnh hưởng score. Đã không kiểm thử bias này; đề xuất `LLMJudge.check_position_bias` chạy swap A/B ở lần eval tiếp theo.

## 3. Problem Solving — vấn đề lớn nhất
- **Vấn đề:** Ban đầu dùng `vectorstore.similarity_search(query)` của LangChain, không lấy được chunk ID thật của ChromaDB — chỉ có nội dung text. Điều này chặn Retrieval Evaluation vì Hit Rate cần so sánh ID.
- **Cách debug:**
  1. Thử `similarity_search_with_relevance_scores` → vẫn không trả ID.
  2. Đọc source LangChain Chroma wrapper → thấy `.vectorstore._collection` là raw ChromaDB Collection.
  3. Chuyển sang `self.vectorstore._collection.query(query_embeddings=[...], include=["documents","metadatas"])` — trả về `raw["ids"][0]` là list chunk ID thật.
- **Bài học:** Khi wrapper "thuận tiện" cắt mất metadata quan trọng (như ID), sẵn sàng xuống tầng raw client. Ghi lại mapping ID ↔ source trong `AGENT_OUTPUT_SAMPLE.md` để team khác debug retrieval không bị mất thời gian.

## 4. Trade-off Chi phí vs Chất lượng
- **Quan sát từ benchmark:** V2 tăng score +0.44 nhưng **latency +4s/case** (từ 3.1s → 7.2s). Nguyên nhân: query expansion gọi LLM thêm 1 lần / query + retrieve 3 query × 5 chunks.
- **Đề xuất tối ưu latency:** Cache query expansion theo hash(question) — trong benchmark mỗi question chạy 1 lần, nhưng prod sẽ có câu hỏi lặp. Dùng query expansion chỉ khi confidence của lần retrieve đầu thấp (adaptive retrieval).
- **Cost của Agent:** Agent dùng `gpt-4o-mini` (rẻ) nên không phải bottleneck. Judge mới là bottleneck — xem `failure_analysis.md §4.3`.

## 5. Bài học rút ra
- Một "optimization" tốt ở mặt quality có thể làm tệ đi metric khác (latency) — cần nhiều metric song song để không "local-optimize".
- Tài liệu có bảng mapping (như Chunk ID → source trong `AGENT_OUTPUT_SAMPLE.md`) giá trị bằng cả file code.
- **Làm khác nếu làm lại:** tách phần embedding (OpenAI call để tính query vector) ra một cache layer — mỗi benchmark run phải embed 50 query × 2 version, tốn $ không đáng có.
- **Câu hỏi mở:** Liệu relevance threshold `0.3` là đúng không? Có case adversarial V2 trả "không tìm thấy" dù có chunk liên quan — có thể do threshold quá cao. Cần A/B test với `0.2` và `0.25`.
