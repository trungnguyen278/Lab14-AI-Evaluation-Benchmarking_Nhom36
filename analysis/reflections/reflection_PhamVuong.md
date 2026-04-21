# Individual Reflection — Phạm Vương

> GitHub: phamvuong2622004 · Email: phamvuong2622004@gmail.com

## 1. Vai trò trong nhóm & đóng góp cụ thể
- **Vai trò:** Data — đồng phụ trách Golden Dataset với Lương Anh.
- **Module phụ trách:**
  - `data/synthetic_gen.py` (iteration đầu) — implement OpenAI Chat Completions call, generate 20 Q&A pairs từ `policy_refund_v4.txt` và `sla_p1_2026.txt`, prompt yêu cầu có câu hỏi "lừa" / hard.
  - Tham gia merge & integrate code SDG trên nhánh `main`.
- **Số commit (no-merges):** 1 (e4a492a "Implement synthetic_gen.py with OpenAI API and generate 20 Q&A pairs").

## 2. Technical Depth — 3 khái niệm cốt lõi

### 2.1 MRR (Mean Reciprocal Rank)
- **Định nghĩa:** MRR = mean(1 / rank_của_kết_quả_đúng_đầu_tiên). Scale [0, 1]; càng cao càng tốt.
- **Ví dụ trong lab:** Câu `"Chính sách hoàn tiền áp dụng từ ngày nào?"` — expected `[doc_19..doc_23]` (chunks của policy_refund_v4). Nếu retriever trả `[doc_19, doc_20, doc_21]` → rank=1, MRR case=1.0. Nếu trả `[doc_5, doc_19, ...]` → rank=2, MRR=0.5.
- **MRR vs Hit Rate:** MRR chi tiết hơn vì phạt thứ hạng thấp; Hit Rate binary. Trong lab V2 có MRR 0.935 > V1 0.92 tuy Hit Rate bằng nhau.

### 2.2 Cohen's Kappa / Multi-Judge
- **Cohen's Kappa:** κ = (pₒ − pₑ) / (1 − pₑ); loại trừ đồng thuận ngẫu nhiên.
- **Trong lab:** Không dùng κ gốc (cần ước lượng phân phối), thay bằng `kappa_like` = tỉ lệ criterion (accuracy/completeness/tone) có exact match giữa 2 judge. V1 = V2 = 0.907.
- **Vì sao cần Multi-Judge cho SDG do mình đóng góp:** Câu hỏi `"Khách hàng có cần cung cấp lý do khi yêu cầu hoàn tiền không?"` (refund policy, do nhóm SDG tạo) là case conflict duy nhất — hai judge chênh 2.67 điểm. Nếu chỉ dùng 1 judge, dataset của mình không bao giờ lộ ra điểm yếu này.

### 2.3 Position Bias
- **Định nghĩa:** Judge có thể thiên vị answer đặt trước/sau trong prompt. Quan trọng khi làm pairwise comparison (A vs B).
- **Đề xuất test:** Chạy lại 10 case có `judge.gap > 0.5`, swap A↔B trong prompt, đo lại. Nếu score đảo chiều → có position bias.

## 3. Problem Solving — vấn đề lớn nhất
- **Vấn đề:** Prompt SDG ban đầu thường sinh ra Q&A có `expected_answer` gần như sao chép nguyên văn 1 câu trong context → câu hỏi quá "easy", không thử thách retrieval + generation. Đồng thời, câu adversarial thường mơ hồ, khó chấm điểm.
- **Cách debug / refine:**
  1. Thêm constraint trong prompt: `{num_pairs - 1} câu thông thường + 1 câu 'lừa' hoặc cực khó` để đảm bảo độ khó phân tầng.
  2. Định nghĩa rõ field `difficulty ∈ {easy, medium, hard}` và `type ∈ {fact-check, reasoning, adversarial}` để downstream có thể aggregate metric theo nhóm.
  3. Chạy thử benchmark với 20 câu đầu → thấy Hit Rate cao cho easy, rất thấp cho adversarial (đúng như kỳ vọng) → feedback loop để refine prompt.
- **Bài học:** SDG cần loop nhanh "generate → benchmark → inspect failure → refine prompt SDG" — không phải "generate 1 lần là xong".

## 4. Trade-off Chi phí vs Chất lượng
- **SDG cost:** ~$0.01 cho 20 Q&A, không phải bottleneck.
- **Tối ưu không phải cost, mà là đa dạng:** Để rubric đạt "Red Teaming phá vỡ hệ thống thành công", câu hỏi hard phải thật sự làm agent V2 fail — ít nhất 2 case adversarial trong lab đã làm V2 trả "không tìm thấy thông tin" (đúng mục tiêu của SDG). Tức là **chất lượng SDG > số lượng**.

## 5. Bài học rút ra
- Generate 20 câu hỏi không khó, nhưng generate 20 câu hỏi **phân tầng difficulty + có GT chunk ID** là khác biệt giữa "demo" và "benchmark chuyên nghiệp".
- **Làm khác nếu làm lại:**
  - Validate prompt output ngay bằng schema (JSON-Schema hoặc `pydantic`) thay vì `json.loads` trần.
  - Seed câu hỏi bằng các "query pattern" quan sát được từ người dùng thật (nếu có log) để golden set gần với production traffic.
- **Câu hỏi mở:** Làm sao đo "độ phủ" của golden set lên không gian query người dùng? Hiện tại ta chỉ cover 5 policy × 10 Q&A × 3 difficulty = 150 kịch bản tiềm năng, chưa rõ có miss hotspot nào không.
