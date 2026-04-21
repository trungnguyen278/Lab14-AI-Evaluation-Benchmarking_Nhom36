import asyncio
import os
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()

from agent.rag_agent_v1 import _get_llm, _get_vectorstore

SYSTEM_PROMPT = """Bạn là trợ lý AI chuyên nghiệp của bộ phận hỗ trợ nội bộ.

QUY TẮC BẮT BUỘC:
1. CHỈ trả lời dựa trên tài liệu được cung cấp bên dưới. KHÔNG bịa thông tin.
2. Nếu tài liệu không chứa đủ thông tin, hãy nói rõ: "Không tìm thấy thông tin trong tài liệu nội bộ."
3. Trích dẫn nguồn tài liệu khi trả lời (tên file nguồn).
4. Trả lời chi tiết, có cấu trúc rõ ràng (dùng bullet points khi cần).
5. Nếu câu hỏi liên quan đến nhiều tài liệu, tổng hợp thông tin từ tất cả nguồn liên quan.
"""


class RagAgentV2:
    """
    RAG Agent V2 — Optimized version.
    - top_k=5 + relevance score filtering
    - Query expansion (LLM rewrite)
    - Detailed system prompt with source citation
    """

    def __init__(self):
        self.name = "SupportAgent-v2"
        self.vectorstore = _get_vectorstore()
        self.llm = _get_llm()
        self.score_threshold = 0.3

    async def _expand_query(self, question: str) -> List[str]:
        """Generate query variants for better retrieval."""
        expand_prompt = (
            f"Viết lại câu hỏi sau thành 2 phiên bản khác nhau để tìm kiếm tài liệu tốt hơn. "
            f"Trả về mỗi phiên bản trên 1 dòng, KHÔNG đánh số.\n\nCâu hỏi gốc: {question}"
        )
        resp = await asyncio.to_thread(self.llm.invoke, expand_prompt)
        variants = [line.strip() for line in resp.content.strip().split("\n") if line.strip()]
        return [question] + variants[:2]

    async def query(self, question: str) -> Dict:
        # Step 1: Query expansion
        queries = await self._expand_query(question)

        # Step 2: Retrieve with scores from all query variants
        all_docs_with_scores: list = []
        seen_contents: set = set()
        for q in queries:
            results = self.vectorstore.similarity_search_with_relevance_scores(q, k=5)
            for doc, score in results:
                if doc.page_content not in seen_contents and score >= self.score_threshold:
                    all_docs_with_scores.append((doc, score))
                    seen_contents.add(doc.page_content)

        # Sort by score descending, take top 5
        all_docs_with_scores.sort(key=lambda x: x[1], reverse=True)
        top_docs = all_docs_with_scores[:5]

        contexts = [doc.page_content for doc, _ in top_docs]
        retrieved_ids = [
            doc.metadata.get("source", doc.metadata.get("id", f"doc_{i}"))
            for i, (doc, _) in enumerate(top_docs)
        ]
        scores = [round(score, 4) for _, score in top_docs]

        # Step 3: Generate with detailed prompt
        context_text = "\n---\n".join(
            f"[Nguồn: {rid}]\n{ctx}" for rid, ctx in zip(retrieved_ids, contexts)
        )
        user_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"TÀI LIỆU THAM KHẢO:\n{context_text}\n\n"
            f"CÂU HỎI: {question}\n\n"
            f"TRẢ LỜI (trích dẫn nguồn):"
        )

        response = await asyncio.to_thread(self.llm.invoke, user_prompt)
        answer = response.content

        return {
            "answer": answer,
            "contexts": contexts,
            "retrieved_ids": retrieved_ids,
            "metadata": {
                "model": self.llm.model_name if hasattr(self.llm, "model_name") else str(self.llm),
                "top_k": 5,
                "version": "v2",
                "sources": retrieved_ids,
                "relevance_scores": scores,
                "query_variants": queries,
            },
        }
