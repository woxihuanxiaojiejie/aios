from __future__ import annotations

from fastapi import APIRouter, status

from aios.api.dependencies import (
    GenerationRecorderDep,
    LifecycleDep,
    LLMAdapterDep,
)
from aios.api.schemas.decision import decision_response
from aios.api.schemas.decision_generation import (
    DecisionGenerationRequest,
    DecisionGenerationResponse,
    generation_metadata_response,
)
from aios.application.decision_generation import DecisionGenerationService

router = APIRouter(prefix="/decision-generation", tags=["decision-generation"])


@router.post(
    "/generate",
    response_model=DecisionGenerationResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_decision(
    request: DecisionGenerationRequest,
    lifecycle: LifecycleDep,
    llm_adapter: LLMAdapterDep,
    generation_recorder: GenerationRecorderDep,
) -> DecisionGenerationResponse:
    service = DecisionGenerationService(
        lifecycle=lifecycle,
        llm_adapter=llm_adapter,
        generation_recorder=generation_recorder,
    )
    result = service.generate(
        experiment_id=request.experiment_id,
        symbol=request.symbol,
        horizon=request.horizon,
    )
    return DecisionGenerationResponse(
        decision=decision_response(result.decision),
        generation=generation_metadata_response(result.generation),
    )
