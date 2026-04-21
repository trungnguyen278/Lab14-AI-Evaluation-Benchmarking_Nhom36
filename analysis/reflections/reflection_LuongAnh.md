# Individual Reflection — Lương Anh - 2A202600472

> GitHub: anhluong447 · Email: anhluog47@gmail.com

## 1. Vai trò trong nhóm & đóng góp cụ thể
- **Vai trò:** Data — chủ script SDG và khởi tạo Golden Dataset.
- **Module phụ trách:**
  - `data/synthetic_gen.py` — phiên bản đầu tiên: đọc 5 tài liệu nội bộ, gọi OpenAI Chat Completions (`gpt-4o-mini`) generate Q&A theo prompt tiếng Việt, yêu cầu có 1 câu adversarial/hard mỗi nhóm.
  - `data/golden_set.jsonl` — bộ 50 cases final (10 câu × 5 tài liệu).
  - `data/docs/` — phối hợp setup 5 tài liệu nội bộ làm nguồn SDG (access control, HR leave, IT helpdesk, refund policy, SLA).
- **Số commit (no-merges):** 3 (d82c91f khởi tạo SDG script, 969373b reversed, 9075a25 init golden set).

## 2. Technical Depth — 3 khái niệm cốt lõi

### 2.1 MRR (Mean Reciprocal Rank)
- **Định nghĩa:** Trung bình reciprocal rank — `mean(1/rank_first_relevant)` trên tập câu hỏi.
- **Liên hệ với SDG:** Để MRR có ý nghĩa, mỗi Q&A phải có `expected_retrieval_ids` là danh sách chunk đúng. Ban đầu `synthetic_gen.py` chỉ output `(question, expected_answer, context)` mà không có ID — dẫn đến retrieval stage không đánh giá được. Đã được sửa: synthetic_gen giờ mapping `source_doc` → chunk IDs toàn cục (ví dụ `policy_refund_v4.txt` → `doc_19..doc_23`).
- **MRR vs Hit Rate:** Hit Rate @ k cho thấy tài liệu đúng CÓ xuất hiện trong top-k không; MRR cho thấy vị trí trung bình. Khi SDG sinh câu hỏi mà có chunk rất gần chunk đúng (ví dụ nhiều Điều khoản trong cùng policy), MRR sẽ giảm nhanh hơn Hit Rate.

### 2.2 Cohen's Kappa / Agreement
- **Vấn đề SDG-level:** Khi SDG tạo câu hỏi "lừa" (adversarial), kỳ vọng 2 judge ít đồng thuận hơn → agreement rate giảm trên nhóm adversarial. Đây là signal "golden set có chất lượng" vì nó tìm ra vùng mà judge rubric cũng chưa rõ.
- **Quan sát lab:** Trong 50 case, conflict duy nhất (`gap 2.67`) rơi đúng vào 1 câu adversarial/semantic-negative do SDG generate — minh chứng adversarial case đang làm nhiệm vụ "phá vỡ hệ thống" như yêu cầu.

### 2.3 Position Bias
- **Định nghĩa:** Trong LLM-as-Judge, kết quả có thể đổi chiều khi swap thứ tự trình bày response.
- **Liên hệ SDG:** Một vài câu hỏi adversarial hỏi "Chính sách X có thay đổi gì so với Y" — nếu Judge prompt đặt ground_truth trước/sau answer ở vị trí khác nhau, kết quả có thể lệch. Đây là lý do cần implement `check_position_bias` trước khi tin tưởng judge score tuyệt đối.

## 3. Problem Solving — vấn đề lớn nhất
- **Vấn đề:** LLM (`gpt-4o-mini`) đôi lúc trả về JSON có code-fence `"""json ... """` hoặc text dư thừa trước/sau — làm `json.loads` fail. Benchmark có thể mất toàn bộ 1 batch nếu không handle.
- **Cách debug:**
  1. Log `response_text[:200]` mỗi lần parse fail để xem pattern.
  2. Thêm fallback: strip `"""json` + `"""` nếu có; dùng regex tìm `{...}` đầu tiên.
  3. Nếu vẫn fail, emit 1 QA pair placeholder để không break pipeline (written trong `synthetic_gen.py:66-75`).
- **Bài học:** Mọi output từ LLM phải có layer "defensive parsing" — giả định LLM sẽ tuân thủ schema 95% là đủ phá benchmark.

## 4. Trade-off Chi phí vs Chất lượng
- **Cost SDG:** 5 tài liệu × 10 Q&A × `gpt-4o-mini` ≈ chỉ vài cent — không phải bottleneck.
- **Chất lượng SDG:** Dùng model **rẻ** (`gpt-4o-mini`) cho SDG tạo ra rủi ro: câu hỏi đôi khi "rập khuôn" (fact-check Q chiếm đa số, hard Q hầu hết chỉ là "compare 2 phiên bản"). Đề xuất:
  - Mix 2 model SDG: 70% `gpt-4o-mini` (volume rẻ) + 30% `gpt-4o` (chất lượng cho adversarial).
  - Review manual 5/50 câu hỏi "hard" trước khi finalize golden set.

## 5. Bài học rút ra
- **SDG quyết định trần điểm của benchmark.** Nếu golden set lệch, mọi metric downstream đều lệch theo. Hit Rate 98% có thể là ảo nếu `expected_retrieval_ids` mapping sai.
- **Làm khác nếu làm lại:**
  - Generate `expected_retrieval_ids` ngay trong lần SDG đầu, không backfill sau — tránh risk mapping sai.
  - Thêm 10 câu hỏi "out-of-corpus" (hỏi thông tin không có trong 5 tài liệu) để test khả năng "Tôi không biết" của agent.
- **Câu hỏi mở:** Làm sao validate chất lượng SDG một cách tự động? Hiện tại ta dựa vào human-review — nhưng nếu scale lên 500 câu hỏi thì không khả thi. Có thể dùng một judge thứ 3 để scoring câu hỏi (Q-quality judge).
