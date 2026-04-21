# Agent Output Sample — V1 vs V2

> **Ngày chạy thử:** 2026-04-21  
> **Câu hỏi test:** `"Chính sách hoàn tiền này áp dụng cho những loại đơn hàng nào?"`  
> **Model:** `gpt-4o-mini`  
> **Datasource:** ChromaDB — collection `day09_docs` (30 chunks, ID toàn cục `doc_0`–`doc_29`)

---

## Sơ đồ Chunk ID trong ChromaDB

ChromaDB đánh ID **toàn cục**, không phải per-file:

| Chunk ID | Source | chunk_index |
|----------|--------|-------------|
| `doc_0` – `doc_6` | `access_control_sop.txt` | 0–6 |
| `doc_7` – `doc_12` | `hr_leave_policy.txt` | 0–5 |
| `doc_13` – `doc_18` | `it_helpdesk_faq.txt` | 0–5 |
| `doc_19` – `doc_23` | `policy_refund_v4.txt` | 0–4 |
| `doc_24` – `doc_29` | `sla_p1_2026.txt` | 0–5 |

---

## RAG Agent V1 — Base Version

### Cấu hình
| Tham số | Giá trị |
|---------|---------|
| `top_k` | 2 |
| Query expansion | ❌ Không |
| Relevance filtering | ❌ Không |
| System prompt | Generic (không có hướng dẫn cụ thể) |
| Source citation | ❌ Không |

### JSON Output

```json
{
  "answer": "Chính sách hoàn tiền này áp dụng cho tất cả các đơn hàng được đặt trên hệ thống nội bộ kể từ ngày 01/02/2026. Các đơn hàng đặt trước ngày có hiệu lực sẽ áp dụng theo chính sách hoàn tiền phiên bản 3.",
  "contexts": [
    "CHÍNH SÁCH HOÀN TIỀN - PHIÊN BẢN 4\n...\n=== Điều 1: Phạm vi áp dụng ===\nChính sách này áp dụng cho tất cả các đơn hàng...",
    "xem xét trong vòng 1 ngày làm việc...\n=== Điều 5: Hình thức hoàn tiền ===\n..."
  ],
  "retrieved_ids": [
    "doc_19",
    "doc_22"
  ],
  "metadata": {
    "model": "gpt-4o-mini",
    "top_k": 2,
    "version": "v1",
    "sources": [
      "policy_refund_v4.txt",
      "policy_refund_v4.txt"
    ]
  }
}
```

### Nhận xét
- Chỉ lấy **2 chunks** (`doc_19`, `doc_22`) → context hẹp, dễ bỏ sót
- `retrieved_ids` là ID thật của ChromaDB — dùng trực tiếp để so sánh với ground truth
- `metadata.sources` chứa tên file gốc tách riêng
- Không có `relevance_scores`, không trích dẫn nguồn trong câu trả lời

---

## RAG Agent V2 — Optimized Version

### Cấu hình
| Tham số | Giá trị |
|---------|---------|
| `top_k` | 5 |
| Query expansion | ✅ Có (2 variants tự động) |
| Relevance filtering | ✅ `score_threshold = 0.3` |
| System prompt | Chi tiết, có quy tắc bắt buộc |
| Source citation | ✅ Có |

### JSON Output

```json
{
  "answer": "Chính sách hoàn tiền này áp dụng cho tất cả các đơn hàng được đặt trên hệ thống nội bộ kể từ ngày 01/02/2026. Các đơn hàng đặt trước ngày có hiệu lực sẽ áp dụng theo chính sách hoàn tiền phiên bản 3.\n\n(Nguồn: policy_refund_v4.txt)",
  "contexts": [
    "CHÍNH SÁCH HOÀN TIỀN - PHIÊN BẢN 4\n...\n=== Điều 1: Phạm vi áp dụng ===\n...",
    "xem xét trong vòng 1 ngày làm việc...\n=== Điều 5: Hình thức hoàn tiền ===\n...",
    "ược quyền yêu cầu hoàn tiền...\n=== Điều 3: Điều kiện áp dụng và ngoại lệ ===\n...",
    "Ngoại lệ không được hoàn tiền:\n- Sản phẩm thuộc danh mục hàng kỹ thuật số...\n=== Điều 4: Quy trình xử lý ===\n...",
    "credit): khách hàng có thể chọn nhận store credit...\n=== Điều 6: Liên hệ và hỗ trợ ===\n..."
  ],
  "retrieved_ids": [
    "doc_19",
    "doc_22",
    "doc_20",
    "doc_21",
    "doc_23"
  ],
  "metadata": {
    "model": "gpt-4o-mini",
    "top_k": 5,
    "version": "v2",
    "sources": [
      "policy_refund_v4.txt",
      "policy_refund_v4.txt",
      "policy_refund_v4.txt",
      "policy_refund_v4.txt",
      "policy_refund_v4.txt"
    ],
    "relevance_scores": [
      0.6375,
      0.5042,
      0.4981,
      0.4978,
      0.4299
    ],
    "query_variants": [
      "Chính sách hoàn tiền này áp dụng cho những loại đơn hàng nào?",
      "Chính sách hoàn tiền này có hiệu lực đối với những loại đơn hàng nào?",
      "Những loại đơn hàng nào được áp dụng chính sách hoàn tiền này?"
    ]
  }
}
```

### Nhận xét
- Lấy đủ **5 chunks** (`doc_19`–`doc_23`) — toàn bộ tài liệu `policy_refund_v4.txt`
- `retrieved_ids` là ID thật của ChromaDB, sắp xếp theo relevance score giảm dần
- **Query expansion** sinh 2 biến thể → tăng recall
- `relevance_scores`: tốt nhất `0.6375`, thấp nhất `0.4299` (đều trên ngưỡng `0.3`)
- Câu trả lời có trích dẫn nguồn `(Nguồn: policy_refund_v4.txt)`

---

## So sánh cấu trúc JSON

| Field | V1 | V2 |
|-------|----|----|
| `answer` | ✅ | ✅ |
| `contexts` | ✅ 2 chunks | ✅ 5 chunks |
| `retrieved_ids` | ✅ ChromaDB IDs | ✅ ChromaDB IDs |
| `metadata.model` | ✅ | ✅ |
| `metadata.top_k` | ✅ | ✅ |
| `metadata.version` | ✅ | ✅ |
| `metadata.sources` | ✅ | ✅ |
| `metadata.relevance_scores` | ❌ | ✅ |
| `metadata.query_variants` | ❌ | ✅ |

---

## Mapping với Evaluation Engine

```python
# retrieval_eval.py — so sánh retrieved_ids với ground truth chunk IDs
result["retrieved_ids"]        # ["doc_19", "doc_22", ...]  ← ID thật ChromaDB
                               # ground truth cũng cần dùng cùng ID này

# llm_judge.py — đánh giá chất lượng câu trả lời
result["answer"]               # → answer_relevance, correctness
result["contexts"]             # → faithfulness / grounding

# metadata phụ trợ
result["metadata"]["sources"]  # → tên file gốc khi cần hiển thị
result["metadata"]["relevance_scores"]  # (v2 only) → phân tích retrieval quality
```
