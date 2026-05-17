import time
import asyncio
from dataclasses import dataclass, field

from app.services.logging_service import get_logger
from app.schemas.evaluation_schema import EvaluationRequest, EvaluationResponse, EvaluationBatchResponse

logger = get_logger(__name__)


@dataclass
class EvalResult:
    question: str
    expected_intent: str
    actual_intent: str
    expected_tool: str
    tools_used: list[str]
    expected_source: str
    sources_retrieved: list[str]
    expected_keywords: list[str]
    answer: str
    keyword_match_score: float
    retrieval_hit: bool
    tool_hit: bool
    latency_ms: float
    passed: bool
    category: str
    notes: str = ""


def _keyword_score(answer: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    answer_lower = answer.lower()
    hits = sum(1 for kw in keywords if kw.lower() in answer_lower)
    return round(hits / len(keywords), 3)


def _retrieval_hit(sources: list[str], expected_source: str) -> bool:
    if not expected_source:
        return True
    return any(expected_source.lower() in s.lower() for s in sources)


def _tool_hit(tools_used: list[str], expected_tool: str) -> bool:
    if not expected_tool:
        return True
    return any(expected_tool.lower() in t.lower() for t in tools_used)


async def _run_single(question: str) -> tuple[dict, float]:
    """Run the agent graph on one question and return (result, latency_ms)."""
    from app.agents.graph import build_agent_graph

    graph = build_agent_graph()
    start = time.perf_counter()
    result = await graph.ainvoke({
        "messages": [{"role": "user", "content": question}],
        "session_id": "eval",
        "metadata": {},
        "steps": [],
        "tool_calls": [],
        "retrieved_docs": [],
        "tickets": [],
        "metrics": [],
    })
    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    return result, latency_ms


class EvaluationService:
    def __init__(self, rag_service=None) -> None:
        self.rag_service = rag_service

    async def evaluate_single(self, request: EvaluationRequest) -> EvaluationResponse:
        result, latency_ms = await _run_single(request.question)

        answer = result.get("final_answer", "")
        tools_used = [tc.get("tool", "") for tc in result.get("tool_calls", [])]
        sources = [
            d.get("source", "") for d in result.get("retrieved_docs", [])
        ] + [
            t.get("source_file", "") for t in result.get("tickets", [])
        ]

        kw_score = _keyword_score(answer, request.expected_keywords)
        r_hit = _retrieval_hit(sources, request.expected_source or "")
        t_hit = _tool_hit(tools_used, request.expected_tool or "")

        # Guardrail test passes if the answer contains "blocked" or "content policy"
        if request.category == "guardrail":
            passed = "content policy" in answer.lower() or "blocked" in answer.lower()
        else:
            passed = kw_score >= 0.4 and (r_hit or t_hit)

        logger.info(
            "eval_single",
            question=request.question[:50],
            kw_score=kw_score,
            retrieval_hit=r_hit,
            tool_hit=t_hit,
            passed=passed,
            latency_ms=latency_ms,
        )

        return EvaluationResponse(
            question=request.question,
            generated_answer=answer,
            expected_answer=request.expected_answer,
            keyword_match_score=kw_score,
            retrieval_hit=r_hit,
            latency_ms=latency_ms,
            passed=passed,
            notes=f"tools={tools_used} intent={result.get('intent')}",
        )

    async def evaluate_batch(self, requests: list[EvaluationRequest]) -> list[EvaluationResponse]:
        results = []
        for i, req in enumerate(requests):
            logger.info("eval_batch_progress", done=i + 1, total=len(requests))
            result = await self.evaluate_single(req)
            results.append(result)
        return results

    async def generate_report(self) -> dict:
        import csv
        from pathlib import Path

        dataset_path = Path("data/mock/evaluation_dataset.csv")
        if not dataset_path.exists():
            return {"error": "evaluation_dataset.csv not found"}

        requests = []
        with open(dataset_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                requests.append(EvaluationRequest(
                    question=row["question"],
                    expected_source=row.get("expected_source") or None,
                    expected_keywords=[k.strip() for k in row.get("expected_keywords", "").split(",") if k.strip()],
                    category=row.get("category"),
                    difficulty=row.get("difficulty"),
                ))

        results = await self.evaluate_batch(requests)

        passed = sum(1 for r in results if r.passed)
        avg_kw = round(sum(r.keyword_match_score for r in results) / len(results), 3)
        avg_lat = round(sum(r.latency_ms for r in results) / len(results), 1)

        return {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "pass_rate": round(passed / len(results) * 100, 1),
            "avg_keyword_match_score": avg_kw,
            "avg_latency_ms": avg_lat,
            "results": [r.model_dump() for r in results],
        }
