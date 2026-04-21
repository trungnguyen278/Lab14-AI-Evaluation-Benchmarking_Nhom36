# Individual Reflection — Nguyễn Thành Trung 2A202600451

> Email: trung2782002@gmail.com · GitHub: trungnguyen278

## 1. Vai trò trong nhóm & đóng góp cụ thể
- **Vai trò:** AI-Backend + DevOps/Analyst — chủ Evaluation Engine, Async Runner, Release Gate, Report schema, Failure Analysis.
- **Module phụ trách:**
  - `engine/llm_judge.py` — Multi-Judge consensus với 2 model OpenAI (`gpt-4o` + `gpt-4-turbo`), parse JSON đầu ra, tính agreement-rate, kappa-like, flag `conflict`, track token usage.
  - `engine/retrieval_eval.py` — Hit Rate @ k + MRR thực (trước đó là placeholder hardcode).
  - `engine/runner.py` — Async `asyncio.gather` theo batch 5 có handle exception, giữ 50 case dưới ~2 phút/phiên bản.
  - `main.py` — orchestrator V1 vs V2, `_release_gate`, ước tính cost USD theo rate card OpenAI, ghi `reports/summary.json` & `benchmark_results.json` đúng schema mẫu thầy cung cấp.
  - `data/golden_set.jsonl` — backfill trường `expected_retrieval_ids` (mapping chunk ID toàn cục `doc_0`–`doc_29`) để Hit Rate/MRR tính được.
  - `analysis/failure_analysis.md` — điền số thật, cluster 2 nhóm lỗi chính, 5-Whys trên 3 case tệ nhất.
  - `.env.example` — chuẩn hoá cấu hình 2 Judge khác model SDG để tránh self-preference bias.

## 2. Technical Depth — 3 khái niệm cốt lõi

### 2.1 MRR (Mean Reciprocal Rank)
- **Định nghĩa:** Trung bình của `1 / rank` tại vị trí đầu tiên một doc đúng xuất hiện trong danh sách retrieved (1-indexed). Nếu không tìm thấy → 0.
- **Trong lab:** `engine/retrieval_eval.py::calculate_mrr`. Ví dụ expected `doc_19`, retrieved `[doc_5, doc_19, doc_7]` → MRR = 1/2 = 0.5.
- **MRR vs Hit Rate @ k:** Hit Rate chỉ quan tâm **có** match trong top-k hay không (0/1), còn MRR phạt nặng khi đúng nhưng xếp thấp. Kết quả V2 có Hit Rate @ 3 = 0.98 giống V1 nhưng MRR tăng 0.92 → 0.935 → query expansion của V2 kéo chunk đúng lên vị trí cao hơn.

### 2.2 Cohen's Kappa & Multi-Judge Agreement
- **Cohen's Kappa:** κ = (p₀ − pₑ) / (1 − pₑ); trong đó `p₀` là tỉ lệ đồng thuận quan sát được, `pₑ` là tỉ lệ đồng thuận do ngẫu nhiên. κ loại trừ trường hợp 2 judge cùng chọn 5 một cách "mù quáng" vì phần lớn case dễ.
- **Trong lab hiện dùng 2 chỉ số:**
  - `agreement_rate` = 1 − |overall_A − overall_B| / 4 (scale-normalised).
  - `kappa_like` = tỉ lệ criterion (accuracy/completeness/tone) mà 2 judge cho cùng số nguyên.
- **Vì sao chưa là Kappa thật:** chưa ước lượng `pₑ` từ phân phối điểm thực tế của từng judge; sẽ cần ≥ 100 case để `pₑ` đủ ổn định. Đây là một trade-off: `kappa_like` rẻ và đủ để bắt conflict case "Khách hàng có cần cung cấp lý do" (gap 2.67), nhưng chưa phân biệt đồng thuận thật với đồng thuận ngẫu nhiên.

### 2.3 Position Bias trong LLM-as-Judge
- **Định nghĩa:** Model chấm thiên vị theo thứ tự xuất hiện của answer (thường ưu tiên answer đầu). Đây là lý do các paper RLHF luôn swap A/B.
- **Implement đề xuất:** `check_position_bias(resp_a, resp_b)` chạy 2 lần — lần 1 prompt theo thứ tự `[A, B]`, lần 2 `[B, A]`; nếu kết luận đảo chiều hoặc score chênh > 0.5 → flag.
- **Case thực tế trong lab:** Case "Khách hàng có cần cung cấp lý do hoàn tiền" — `gpt-4o` cho 2.33, `gpt-4-turbo` cho 5.0; nếu chỉ dùng 1 judge và thứ tự prompt cố định, ta sẽ không phát hiện được semantic equivalence bị bỏ sót. Position-bias sẽ làm kết quả trên tệ hơn nữa.

## 3. Problem Solving — vấn đề lớn nhất
- **Vấn đề:** Sau lần chạy đầu, schema output của mình (`benchmark_results.json` là flat list V2) không khớp với mẫu thầy cung cấp (`{"v1": [...], "v2": [...]}`, có `ragas.faithfulness`, `judge.individual_results`, `judge.status`). Nếu re-run benchmark để đổi format sẽ tốn thêm $0.39 + 4 phút.
- **Cách debug:**
  1. Diff 2 schema bằng script Python duyệt keys deep.
  2. Viết `_to_teacher_case()` trong `main.py` để chuyển đổi từ struct nội bộ → schema thầy (giữ keys cũ + thêm keys thầy yêu cầu).
  3. Chạy transform **offline** trên JSON đã lưu — không gọi API.
- **Bài học:** Always dump raw results first, transform later — tách "collection" khỏi "presentation layer" thì khi yêu cầu schema thay đổi không phải re-run pipeline.

## 4. Trade-off Chi phí vs Chất lượng
- **Cost hiện tại:** $0.39 / 50 cases / phiên bản. 83% chi phí (~$0.32) đến từ `gpt-4-turbo` (Judge B).
- **Đề xuất giảm 30% cost** (đã viết trong `failure_analysis.md §4.3`): Adaptive Judge — case `difficulty=hard` hoặc `type=adversarial` vẫn dùng `gpt-4-turbo`; case `easy/medium` swap xuống `gpt-3.5-turbo` (rẻ hơn ~10x). Dự kiến giảm cost ~60% mà vẫn giữ khả năng phát hiện conflict trên các case khó — nơi multi-judge tạo ra value thật sự.
- **Không làm gì:** Không giảm xuống Single-Judge vì sẽ phạm "điểm liệt" rubric. Không downgrade Judge A xuống `gpt-4o-mini` vì đó chính là model SDG → self-preference bias.

## 5. Bài học rút ra
- Evaluation là **một hệ thống phần mềm** — không phải "chạy notebook 1 lần rồi nộp". Cần schema rõ ràng, reproducibility (`.env.example`), cost budget, retry logic, và cách debug khi benchmark fail.
- **Multi-Judge không chỉ vì rubric** — 1 conflict case duy nhất trong 50 (2%) đã minh chứng: Single-Judge sẽ giấu đi 1 blind-spot của judge rubric. Giá trị Multi-Judge lớn hơn giá trị kỳ vọng khi có cases biên (adversarial, negative-existence).
- **Làm khác nếu làm lại:** implement `check_position_bias` ngay từ ngày 1, không để làm "placeholder". Dùng `pytest-asyncio` viết unit test cho mỗi engine module trước khi chạy full benchmark — rẻ hơn nhiều so với debug bằng cách re-run 100-case pipeline.
- **Câu hỏi mở:** Khi golden set được generate bởi gpt-4o-mini, làm sao đo được "upper-bound" của agent khi bản thân ground-truth có thể có bias? → cần human-audit 10 cases làm "gold-of-gold".
