"""Lab Day 14 — Benchmark orchestrator.

Runs the RAG Agent in two versions (V1 baseline vs V2 optimized), evaluates each
with the real Retrieval-Evaluator + two-model OpenAI Judge, then decides a
Release Gate verdict based on quality, cost, and latency deltas.

Cost note: each case = 2 judge calls (gpt-4o + gpt-4-turbo) + 1 agent call.
50 cases × 2 versions ≈ 300 OpenAI calls. Judges deliberately avoid
gpt-4o-mini since the golden set was generated with that model —
reusing it as Judge would cause self-preference bias.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Dict, List

from agent.main_agent import MainAgent
from engine.llm_judge import LLMJudge, aggregate_usage
from engine.retrieval_eval import RetrievalEvaluator
from engine.runner import BenchmarkRunner

# Approx OpenAI rate card (USD per 1K tokens) — update when pricing changes.
PRICE_PER_1K = {
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.00060},
    "gpt-4o":      {"prompt": 0.00250, "completion": 0.01000},
    "gpt-4-turbo": {"prompt": 0.01000, "completion": 0.03000},
}


def _to_teacher_case(r: Dict) -> Dict:
    """Conform a raw case result to the teacher-provided schema.

    Keeps all our enriched fields and *adds* the teacher-expected ones:
    - test_case (alias for question)
    - ragas {hit_rate, mrr, faithfulness, relevancy}
    - judge.individual_results {<model>: {score, reasoning}}
    - judge.status ("consensus" | "conflict")
    """
    if r.get("status") == "error":
        return r  # pass-through; teacher schema has no error shape

    judge = r["judge"]
    individual = judge.get("individual_scores") or judge.get("individual_results") or {}

    # Derive faithfulness / relevancy from judge rubric scores so every case has real numbers.
    accuracies = [v.get("accuracy") for v in individual.values() if isinstance(v.get("accuracy"), (int, float))]
    completenesses = [v.get("completeness") for v in individual.values() if isinstance(v.get("completeness"), (int, float))]
    faithfulness = round(sum(accuracies) / len(accuracies) / 5.0, 3) if accuracies else 0.0
    relevancy = round(sum(completenesses) / len(completenesses) / 5.0, 3) if completenesses else 0.0

    individual_results = {
        model: {
            "score": v.get("overall", v.get("score", 0)),
            "reasoning": v.get("reasoning", ""),
            "accuracy": v.get("accuracy"),
            "completeness": v.get("completeness"),
            "tone": v.get("tone"),
        }
        for model, v in individual.items()
    }

    retrieval = r.get("retrieval", {})
    return {
        "test_case": r["question"],
        "question": r["question"],
        "expected_answer": r.get("expected_answer"),
        "difficulty": r.get("difficulty"),
        "type": r.get("type"),
        "source_doc": r.get("source_doc", ""),
        "expected_retrieval_ids": r.get("expected_retrieval_ids", []),
        "agent_response": r["agent_response"],
        "retrieved_ids": r.get("retrieved_ids", []),
        "agent_metadata": r.get("agent_metadata", {}),
        "latency": r["latency"],
        "ragas": {
            "hit_rate": retrieval.get("hit_rate", 0.0),
            "mrr": retrieval.get("mrr", 0.0),
            "faithfulness": faithfulness,
            "relevancy": relevancy,
        },
        "judge": {
            "final_score": judge["final_score"],
            "agreement_rate": judge["agreement_rate"],
            "kappa_like": judge.get("kappa_like"),
            "gap": judge.get("gap"),
            "individual_results": individual_results,
            "status": "conflict" if judge.get("conflict") else "consensus",
            "usage": judge.get("usage", {}),
        },
        "status": r["status"],
    }


def _estimate_cost(usage_by_model: Dict[str, Dict[str, int]]) -> Dict[str, float]:
    total = 0.0
    per_model: Dict[str, float] = {}
    for model, counts in usage_by_model.items():
        rate = PRICE_PER_1K.get(model, {"prompt": 0.0, "completion": 0.0})
        cost = (counts["prompt_tokens"] / 1000.0) * rate["prompt"] + (
            counts["completion_tokens"] / 1000.0
        ) * rate["completion"]
        per_model[model] = round(cost, 5)
        total += cost
    return {"total_usd": round(total, 5), "per_model_usd": per_model}


def _summarise(results: List[Dict], version: str) -> Dict:
    graded = [r for r in results if r.get("status") != "error"]
    total = len(graded)
    fails = [r for r in graded if r["status"] == "fail"]

    retrieval_graded = [r for r in graded if r["retrieval"].get("has_ground_truth")]
    hit_rate = (
        sum(r["retrieval"]["hit_rate"] for r in retrieval_graded) / len(retrieval_graded)
        if retrieval_graded
        else 0.0
    )
    mrr = (
        sum(r["retrieval"]["mrr"] for r in retrieval_graded) / len(retrieval_graded)
        if retrieval_graded
        else 0.0
    )

    avg_score = sum(r["judge"]["final_score"] for r in graded) / total if total else 0.0
    avg_agreement = sum(r["judge"]["agreement_rate"] for r in graded) / total if total else 0.0
    avg_kappa = sum(r["judge"]["kappa_like"] for r in graded) / total if total else 0.0
    avg_latency = sum(r["latency"] for r in graded) / total if total else 0.0
    conflict_count = sum(1 for r in graded if r["judge"].get("conflict"))

    usage_total = aggregate_usage([r["judge"]["usage"] for r in graded])
    cost = _estimate_cost(usage_total)

    return {
        "metadata": {
            "version": version,
            "total": total,
            "fail_count": len(fails),
            "error_count": len(results) - total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "metrics": {
            "avg_score": round(avg_score, 3),
            "pass_rate": round((total - len(fails)) / total, 3) if total else 0.0,
            "hit_rate": round(hit_rate, 3),
            "mrr": round(mrr, 3),
            "agreement_rate": round(avg_agreement, 3),
            "kappa_like": round(avg_kappa, 3),
            "conflict_count": conflict_count,
            "avg_latency_sec": round(avg_latency, 3),
        },
        "cost": cost,
        "judge_usage_tokens": usage_total,
    }


def _release_gate(v1: Dict, v2: Dict) -> Dict:
    """Auto Release-Gate: V2 must not regress quality/retrieval and must stay under cost ceiling."""
    score_delta = v2["metrics"]["avg_score"] - v1["metrics"]["avg_score"]
    hit_delta = v2["metrics"]["hit_rate"] - v1["metrics"]["hit_rate"]
    latency_delta = v2["metrics"]["avg_latency_sec"] - v1["metrics"]["avg_latency_sec"]
    cost_ratio = (
        v2["cost"]["total_usd"] / v1["cost"]["total_usd"] if v1["cost"]["total_usd"] > 0 else 1.0
    )

    reasons: List[str] = []
    approve = True
    if score_delta < 0:
        approve = False
        reasons.append(f"Judge score regressed by {score_delta:.2f}")
    if hit_delta < -0.02:
        approve = False
        reasons.append(f"Hit rate regressed by {-hit_delta:.2f}")
    if cost_ratio > 2.0:
        approve = False
        reasons.append(f"Cost grew {cost_ratio:.1f}x (ceiling 2x)")
    if latency_delta > 5.0:
        reasons.append(f"Latency grew by {latency_delta:.1f}s (warning, not blocking)")

    return {
        "decision": "APPROVE" if approve else "BLOCK",
        "score_delta": round(score_delta, 3),
        "hit_rate_delta": round(hit_delta, 3),
        "latency_delta_sec": round(latency_delta, 3),
        "cost_ratio_v2_over_v1": round(cost_ratio, 3),
        "reasons": reasons,
    }


async def _run_version(dataset: List[Dict], version: str) -> Dict:
    print(f"\n🚀 Benchmark {version} on {len(dataset)} cases ...")
    agent = MainAgent(version=version)
    retrieval_eval = RetrievalEvaluator(top_k=3)
    judge = LLMJudge()

    runner = BenchmarkRunner(agent, retrieval_eval, judge)
    start = time.perf_counter()
    results = await runner.run_all(dataset, batch_size=10)
    elapsed = time.perf_counter() - start

    summary = _summarise(results, f"Agent_{version.upper()}")
    summary["metadata"]["wall_clock_sec"] = round(elapsed, 2)
    print(
        f"   ✓ {version} done in {elapsed:.1f}s — score={summary['metrics']['avg_score']}, "
        f"hit={summary['metrics']['hit_rate']}, cost=${summary['cost']['total_usd']}"
    )
    return {"results": results, "summary": summary}


async def _run_position_bias(results: List[Dict], judge: LLMJudge, top_n: int = 10) -> Dict:
    """Pick the N cases with the largest judge gap (or highest score) and re-score
    them with the answer/ground-truth blocks swapped. A `flipped` case means Judge A
    scored the same answer differently based on text position — genuine bias."""
    graded = [r for r in results if r.get("status") != "error" and r.get("judge")]
    if not graded:
        return {"tested": 0, "flipped": 0, "cases": [], "usage": {}}

    # Rank by gap descending — the cases where judges disagreed are where bias would
    # compound. If gaps are all near zero, fall back to the top scorers.
    ranked = sorted(graded, key=lambda r: (r["judge"].get("gap", 0), r["judge"]["final_score"]), reverse=True)
    picked = ranked[:top_n]

    async def _one(r):
        bias = await judge.check_position_bias(
            question=r["question"],
            answer=r["agent_response"],
            ground_truth=r.get("expected_answer", ""),
        )
        return {
            "question": r["question"],
            "difficulty": r.get("difficulty"),
            "type": r.get("type"),
            "judge_gap": r["judge"].get("gap"),
            **bias,
        }

    bias_results = await asyncio.gather(*[_one(r) for r in picked], return_exceptions=True)
    clean = [b for b in bias_results if not isinstance(b, Exception)]
    flipped = sum(1 for b in clean if b.get("flipped"))
    usage_totals = {"prompt_tokens": 0, "completion_tokens": 0}
    for b in clean:
        u = b.get("usage") or {}
        usage_totals["prompt_tokens"] += u.get("prompt_tokens", 0)
        usage_totals["completion_tokens"] += u.get("completion_tokens", 0)

    return {
        "tested": len(clean),
        "flipped": flipped,
        "flip_rate": round(flipped / len(clean), 3) if clean else 0.0,
        "cases": clean,
        "usage": {judge.model_a: usage_totals},
    }


async def main():
    if not os.path.exists("data/golden_set.jsonl"):
        print("❌ Missing data/golden_set.jsonl — run `python data/synthetic_gen.py` first.")
        return

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]
    if not dataset:
        print("❌ data/golden_set.jsonl is empty.")
        return

    v1 = await _run_version(dataset, "v1")
    v2 = await _run_version(dataset, "v2")

    gate = _release_gate(v1["summary"], v2["summary"])

    # Position-bias sanity check on Judge A — 10 worst-disagreement cases from V2.
    print("\n🔍 Position-bias test on top-10 highest-gap V2 cases ...")
    bias_judge = LLMJudge()
    position_bias = await _run_position_bias(v2["results"], bias_judge, top_n=10)
    bias_cost = _estimate_cost(position_bias["usage"])
    print(
        f"   ✓ {position_bias['flipped']}/{position_bias['tested']} cases flipped "
        f"(delta>0.5)  — extra cost ${bias_cost['total_usd']}"
    )

    print("\n📊 --- REGRESSION (V1 vs V2) ---")
    print(f"V1 score: {v1['summary']['metrics']['avg_score']}  "
          f"hit: {v1['summary']['metrics']['hit_rate']}  "
          f"cost: ${v1['summary']['cost']['total_usd']}")
    print(f"V2 score: {v2['summary']['metrics']['avg_score']}  "
          f"hit: {v2['summary']['metrics']['hit_rate']}  "
          f"cost: ${v2['summary']['cost']['total_usd']}")
    print(f"Δ score: {gate['score_delta']:+.3f}   Δ hit: {gate['hit_rate_delta']:+.3f}   "
          f"cost×{gate['cost_ratio_v2_over_v1']}")

    os.makedirs("reports", exist_ok=True)

    # summary.json — teacher schema keys + our enriched superset
    v1_metrics = v1["summary"]["metrics"]
    v2_metrics = v2["summary"]["metrics"]
    regression_block = {
        "v1": {
            "score": v1_metrics["avg_score"],
            "hit_rate": v1_metrics["hit_rate"],
            "judge_agreement": v1_metrics["agreement_rate"],
            **v1_metrics,
        },
        "v2": {
            "score": v2_metrics["avg_score"],
            "hit_rate": v2_metrics["hit_rate"],
            "judge_agreement": v2_metrics["agreement_rate"],
            **v2_metrics,
        },
        "decision": gate["decision"],
        "gate": gate,
    }
    submission_summary = {
        **v2["summary"],
        "metadata": {
            **v2["summary"]["metadata"],
            "versions_compared": ["V1", "V2"],
        },
        "regression": regression_block,
        "position_bias": {
            "model": bias_judge.model_a,
            "tested": position_bias["tested"],
            "flipped": position_bias["flipped"],
            "flip_rate": position_bias["flip_rate"],
            "extra_cost_usd": bias_cost["total_usd"],
            "cases": position_bias["cases"],
        },
    }
    submission_summary["metrics"]["position_bias_flipped"] = position_bias["flipped"]
    submission_summary["metrics"]["position_bias_tested"] = position_bias["tested"]
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(submission_summary, f, ensure_ascii=False, indent=2)

    # benchmark_results.json — teacher schema: {"v1": [...], "v2": [...]}
    combined = {
        "v1": [_to_teacher_case(r) for r in v1["results"]],
        "v2": [_to_teacher_case(r) for r in v2["results"]],
    }
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    print(f"\n🧭 RELEASE GATE: {gate['decision']}")
    for r in gate["reasons"]:
        print(f"   - {r}")


if __name__ == "__main__":
    asyncio.run(main())
