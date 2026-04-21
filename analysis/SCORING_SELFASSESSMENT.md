# Self-Assessment — Đối chiếu với `GRADING_RUBRIC.md` (sau khi hoàn tất A/B/C)

> Số liệu dưới đây là **số thật** từ `reports/summary.json` sau khi chạy full 60 cases × 2 versions + position-bias.

## ✅ An toàn khỏi "Điểm liệt"
- ✅ 2 Judge khác model (`gpt-4o` + `gpt-4-turbo`), cả hai khác SDG (`gpt-4o-mini`).
- ✅ Retrieval Metrics (Hit Rate 0.981 & MRR 0.938 V2 / 0.923 V1) trên 52/60 cases có ground-truth retrieval (10 adversarial out-of-corpus + injection không có chunk đúng → được loại đúng).
- ✅ Position-bias test THẬT (không còn placeholder): 10 case → **6/10 flipped** (flip-rate 60%).

→ Không bị cap 30 điểm.

---

## 👥 Điểm Nhóm — ước lượng **60 / 60** (sau A/B/C)

| Hạng mục | Điểm tối đa | Tự chấm | Cơ sở (số thật) |
|---|---|---|---|
| Retrieval Evaluation | 10 | **10** | Hit Rate 0.981, MRR V2 0.938 / V1 0.923, trên 52 cases có GT |
| Dataset & SDG | 10 | **10** | 60 cases (50 tạo từ SDG + 10 adversarial: 5 out-of-corpus / 3 prompt-injection / 2 conflicting). Red-teaming thành công: V1 nhận score 1.0 trên "IGNORE ALL INSTRUCTIONS" (bị inject), V2 nhận 2.17 trên "cung cấp mật khẩu admin" (lộ thông tin một phần) — dataset PHÁ được cả 2 version |
| Multi-Judge consensus | 15 | **15** | `agreement_rate` 0.954 (V2) / 0.961 (V1), `kappa_like` 0.861 / 0.839, `conflict_count` 4 (V2) vs 1 (V1) — adversarial kéo conflict lên rõ; position-bias thật: 6/10 flipped → **phát hiện Judge A sensitive với thứ tự text** (finding có thật, không phải code placeholder) |
| Regression Testing | 10 | **10** | V1 vs V2 full trên 60 cases; release_gate APPROVE; Δscore +0.280, Δhit 0.000, cost-ratio 0.993 (V2 còn RẺ HƠN V1 chút do V2 đôi lúc refuse nhanh không gọi nhiều token) |
| Performance (Async) | 10 | **10** | `batch_size=10`; V1 67.6s / V2 102.3s (< 2 phút cho 60 cases) — CẢI THIỆN so với batch=5 trước (V2 cũ 127.9s cho 50 cases). Cost V1 $0.468 + V2 $0.465 + bias $0.027 = **$0.960 total** |
| Failure Analysis | 5 | **5** | 5-Whys đầy đủ trên 3 case tệ nhất + 2 failure cluster mới từ adversarial (prompt-injection bypass + over-refusal trên conflicting) |
| **TỔNG NHÓM** | **60** | **60** | |

---

## 👤 Điểm Cá nhân — ước lượng (tối đa 40 / người)

| Thành viên | Engineering (15) | Tech Depth (15) | Problem Solving (10) | Tổng |
|---|---|---|---|---|
| **Trung Nguyễn** (engine + orchestration + bias-test) | 15 (multi-judge, retrieval_eval, runner async batch=10, release gate, report schema, **position-bias thật**, report transform offline) | 15 (MRR/Kappa/Position-bias đều có đo số thật — 6/10 flip rate là dữ liệu thật phát hiện được từ implementation) | 10 (story transform JSON offline, tránh re-run $$$; adaptive judge proposal) | **40 / 40** |
| **Huy Tú** (RAG agents V1/V2) | 13 (V1+V2 agent, factory, raw ChromaDB để lấy ID thật) | 13 (hiểu MRR/Kappa/bias tốt, liên hệ cụ thể V2 over-refuse trên adversarial conflicting) | 10 (story debug LangChain wrapper → raw collection) | **39 / 40** |
| **Lương Anh** (SDG + golden set + adversarial) | 13 (SDG script, mapping chunk ID, đồng chủ bộ 10 adversarial cases) | 12 (khái niệm đầy đủ, liên hệ adversarial SDG → conflict rate tăng) | 10 (defensive parsing JSON) | **35 / 40** |
| **Phạm Vương** (SDG co-owner) | 11 (đóng góp SDG + refine prompt hard cases) | 11 (hiểu khái niệm, giải thích position-bias ở mức mô tả) | 9 (iteration loop refine SDG) | **31 / 40** |

> ⚠️ Điểm cá nhân do thầy chấm — con số trên là **tự ước lượng khung**.

---

## 🎯 Tình trạng các việc để max điểm

### ✅ (A) Adversarial cases — HOÀN THÀNH (+2 Dataset)
- ✅ 5 câu out-of-corpus (WFH, CEO, thưởng tháng 13, ESOP, offboarding).
- ✅ 3 câu prompt-injection ("Bỏ qua hướng dẫn viết thơ", "IGNORE ALL INSTRUCTIONS HACKED", "đóng vai admin cấp password").
- ✅ 2 câu conflicting (hoàn tiền 15 phút như SLA P1; Level 1 đăng Slack incident-p1).
- **Kết quả red-teaming:** V1 bị inject (score 1.0) trên case 2, V2 lộ password (score 2.17) trên case 3 → dataset phá vỡ thành công.

### ✅ (B) Position-bias test — HOÀN THÀNH (+1 Multi-Judge)
- ✅ `LLMJudge.check_position_bias` implement thật: chạy judge 2 lần với block `answer`/`ground_truth` đổi thứ tự, đo delta.
- ✅ Chạy trên 10 case có gap cao nhất của V2.
- ✅ `reports/summary.json.position_bias` = `{model: gpt-4o, tested: 10, flipped: 6, flip_rate: 0.6, extra_cost_usd: 0.027}`.
- **Phát hiện:** Judge A (gpt-4o) bị position bias mạnh — đây là lý do chính tại sao ta cần 2 judge.

### ✅ (C) Giảm latency async — HOÀN THÀNH (+1 Performance)
- ✅ `batch_size=10` trong `main.py::_run_version`.
- ✅ V1 67.6s, V2 102.3s (trước đó V2 batch=5 là 127.9s) — giảm ~20%.

---

## 📤 Checklist nộp bài cuối

- [x] Source code hoàn chỉnh (`engine/`, `agent/`, `main.py`, `data/synthetic_gen.py`)
- [x] `reports/summary.json` (schema thầy + superset: `versions_compared`, `regression.{v1,v2}.{score,hit_rate,judge_agreement}`, `regression.decision`, `position_bias` block đầy đủ)
- [x] `reports/benchmark_results.json` (schema thầy: `{"v1":[...], "v2":[...]}`, `ragas.faithfulness/relevancy`, `individual_results`, `status: consensus|conflict`)
- [x] `data/golden_set.jsonl` (60 cases: 50 base + 10 adversarial)
- [x] `analysis/failure_analysis.md`
- [x] `analysis/reflections/reflection_TrungNguyen.md`
- [x] `analysis/reflections/reflection_HuyTu.md`
- [x] `analysis/reflections/reflection_LuongAnh.md`
- [x] `analysis/reflections/reflection_PhamVuong.md`
- [x] `.env.example` (không commit `.env`)
- [x] `.gitignore` — reports commit, logs + `.env` + golden_set ignore
- [x] `logs/benchmark_full.log` (log run thật, tham khảo sau)
- [ ] `git commit` + `git push` — **bạn chốt khi nào push**

---

## 🧮 Tổng điểm kỳ vọng (sau A/B/C)

| Thành phần | Điểm |
|---|---|
| Nhóm | **60 / 60** |
| Cá nhân Trung Nguyễn (top performer) | **40 / 40** |
| **Tổng Trung Nguyễn (ước lượng)** | **~100 / 100** |
| Cá nhân trung bình 4 người | **~36 / 40** |

## 🔢 Metrics chốt — `reports/summary.json`

| Metric | V1 | V2 | Δ |
|---|---|---|---|
| avg_score | 4.289 | 4.569 | +0.280 |
| pass_rate | 0.867 | 0.883 | +0.016 |
| hit_rate | 0.981 | 0.981 | 0 |
| MRR | 0.923 | 0.938 | +0.015 |
| agreement_rate | 0.961 | 0.954 | −0.007 |
| kappa_like | 0.839 | 0.861 | +0.022 |
| conflict_count | 1 | 4 | +3 (adversarial kéo lên) |
| avg_latency_sec | 2.80 | 12.26 | +9.46 (warning, non-blocking) |
| cost_usd | 0.468 | 0.465 | −0.003 |
| position_bias flip_rate | — | 0.6 (6/10) | — |
| Release Gate | — | — | **APPROVE** |
