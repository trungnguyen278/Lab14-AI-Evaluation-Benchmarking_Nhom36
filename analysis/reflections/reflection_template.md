# Individual Reflection — [Họ và tên SV]

> Copy file này thành `reflection_[Tên_SV].md` trong cùng thư mục và điền vào các mục dưới.

## 1. Vai trò trong nhóm & đóng góp cụ thể
- **Vai trò:** (Data / AI-Backend / DevOps-Analyst)
- **Module bạn phụ trách:**
- **Đóng góp nổi bật** (link tới PR / commit / file cụ thể, ví dụ `engine/llm_judge.py:60-90`):
- **Số commit bạn làm:** (chạy `git log --author="<email>" --oneline | wc -l`)

## 2. Technical Depth — giải thích 3 khái niệm cốt lõi
### 2.1 MRR (Mean Reciprocal Rank)
- Định nghĩa:
- Cách tính trong lab này:
- Vì sao MRR khác với Hit Rate @ k?

### 2.2 Cohen's Kappa / Multi-Judge Agreement
- Định nghĩa:
- Trong lab, bạn đang dùng chỉ số gì (`agreement_rate` hay `kappa_like`) và tại sao?
- Nhược điểm của chỉ số "exact match" so với Cohen's Kappa thật:

### 2.3 Position Bias trong LLM-as-Judge
- Định nghĩa:
- Lab đã có `check_position_bias` chưa? Nếu chưa, đề xuất cách implement:
- Một ví dụ thực tế khi position-bias làm sai lệch benchmark:

## 3. Problem Solving — vấn đề lớn nhất bạn phải giải
- **Mô tả vấn đề:**
- **Cách bạn debug:**
- **Kết quả / bài học:**

## 4. Trade-off Chi phí vs Chất lượng
- Khi nào bạn chọn model rẻ hơn cho Judge?
- Chi phí / 50 cases hiện tại: **$0.39** (V2). Bạn đề xuất phương án nào để giảm 30%?
- Bạn đã thử thay đổi gì chưa? Kết quả?

## 5. Bài học rút ra
- Điều bạn học được về AI Evaluation:
- Điều bạn sẽ làm khác đi nếu làm lại:
- Một câu hỏi mở còn tồn đọng:
