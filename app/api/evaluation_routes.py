from fastapi import APIRouter, Depends
from app.schemas.evaluation_schema import EvaluationRequest, EvaluationResponse, EvaluationBatchResponse
from app.services.evaluation_service import EvaluationService
from app.dependencies import require_api_key

router = APIRouter()

# Single shared instance — avoids rebuilding the agent graph on every request
_service = EvaluationService()


@router.post("/run", response_model=EvaluationResponse)
async def evaluate_single(request: EvaluationRequest, _: None = Depends(require_api_key)):
    return await _service.evaluate_single(request)


@router.post("/batch", response_model=EvaluationBatchResponse)
async def evaluate_batch(requests: list[EvaluationRequest], _: None = Depends(require_api_key)):
    results = await _service.evaluate_batch(requests)
    passed = sum(1 for r in results if r.passed)
    avg_lat = round(sum(r.latency_ms for r in results) / max(len(results), 1), 1)
    return EvaluationBatchResponse(
        results=results,
        total=len(results),
        passed=passed,
        failed=len(results) - passed,
        avg_latency_ms=avg_lat,
    )


@router.get("/report")
async def get_evaluation_report(_: None = Depends(require_api_key)):
    return await _service.generate_report()
