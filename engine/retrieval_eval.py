"""Retrieval-stage evaluation: Hit Rate @ k and MRR.

Evaluation is purely arithmetic — no LLM calls — so it costs $0 to run.
"""

from __future__ import annotations

from typing import Dict, List


class RetrievalEvaluator:
    def __init__(self, top_k: int = 3):
        self.top_k = top_k

    def calculate_hit_rate(
        self, expected_ids: List[str], retrieved_ids: List[str], top_k: int | None = None
    ) -> float:
        """1.0 if any expected_id appears in the first `top_k` retrieved IDs, else 0.0."""
        k = top_k or self.top_k
        top_retrieved = retrieved_ids[:k]
        return 1.0 if any(doc_id in top_retrieved for doc_id in expected_ids) else 0.0

    def calculate_mrr(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        """Reciprocal rank of the first expected_id found in retrieved_ids. 0 if not found."""
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    def score_case(self, test_case: Dict, agent_response: Dict) -> Dict[str, float]:
        """Per-case retrieval metrics — returned shape is what the runner expects."""
        expected = test_case.get("expected_retrieval_ids", []) or []
        retrieved = agent_response.get("retrieved_ids", []) or []
        if not expected:
            # No ground truth → mark as N/A (still countable, don't penalise the agent)
            return {"hit_rate": 0.0, "mrr": 0.0, "has_ground_truth": False}
        return {
            "hit_rate": self.calculate_hit_rate(expected, retrieved),
            "mrr": self.calculate_mrr(expected, retrieved),
            "has_ground_truth": True,
        }

    async def evaluate_batch(self, pairs: List[Dict]) -> Dict[str, float]:
        """Aggregate hit_rate / MRR over a list of {'case': ..., 'response': ...} pairs."""
        scored = [self.score_case(p["case"], p["response"]) for p in pairs]
        graded = [s for s in scored if s["has_ground_truth"]]
        if not graded:
            return {"avg_hit_rate": 0.0, "avg_mrr": 0.0, "graded_count": 0}
        return {
            "avg_hit_rate": round(sum(s["hit_rate"] for s in graded) / len(graded), 4),
            "avg_mrr": round(sum(s["mrr"] for s in graded) / len(graded), 4),
            "graded_count": len(graded),
        }
