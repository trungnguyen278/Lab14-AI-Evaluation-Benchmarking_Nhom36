"""Async benchmark runner.

Orchestrates: agent.query  →  retrieval metrics  →  multi-judge.
Each case runs concurrently (bounded by `batch_size`) to keep the whole
50-case sweep under 2 minutes as the rubric requires.
"""

from __future__ import annotations

import asyncio
import time
from typing import Dict, List


class BenchmarkRunner:
    def __init__(self, agent, retrieval_evaluator, judge):
        self.agent = agent
        self.retrieval_evaluator = retrieval_evaluator
        self.judge = judge

    async def run_single_test(self, test_case: Dict) -> Dict:
        start_time = time.perf_counter()

        # 1. Agent query
        response = await self.agent.query(test_case["question"])
        latency = time.perf_counter() - start_time

        # 2. Retrieval metrics (pure arithmetic, no API)
        retrieval_scores = self.retrieval_evaluator.score_case(test_case, response)

        # 3. Multi-Judge (2 OpenAI models in parallel)
        judge_result = await self.judge.evaluate_multi_judge(
            test_case["question"],
            response["answer"],
            test_case["expected_answer"],
        )

        return {
            "question": test_case["question"],
            "expected_answer": test_case["expected_answer"],
            "difficulty": test_case.get("difficulty", "unknown"),
            "type": test_case.get("type", "unknown"),
            "source_doc": test_case.get("source_doc", ""),
            "expected_retrieval_ids": test_case.get("expected_retrieval_ids", []),
            "agent_response": response["answer"],
            "retrieved_ids": response.get("retrieved_ids", []),
            "agent_metadata": response.get("metadata", {}),
            "latency": round(latency, 3),
            "retrieval": retrieval_scores,
            "judge": judge_result,
            "status": "fail" if judge_result["final_score"] < 3 else "pass",
        }

    async def run_all(self, dataset: List[Dict], batch_size: int = 5) -> List[Dict]:
        """Run all cases in bounded concurrency batches."""
        results: List[Dict] = []
        for i in range(0, len(dataset), batch_size):
            batch = dataset[i : i + batch_size]
            batch_results = await asyncio.gather(
                *(self.run_single_test(case) for case in batch),
                return_exceptions=True,
            )
            for case, res in zip(batch, batch_results):
                if isinstance(res, Exception):
                    results.append(
                        {
                            "question": case["question"],
                            "error": f"{type(res).__name__}: {res}",
                            "status": "error",
                        }
                    )
                else:
                    results.append(res)
        return results
