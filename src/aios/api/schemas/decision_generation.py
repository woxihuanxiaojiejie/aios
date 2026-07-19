from __future__ import annotations

from pydantic import Field

from aios.api.schemas.common import ApiSchema
from aios.api.schemas.decision import DecisionResponse
from aios.application.decision_generation import GenerationMetadata


class DecisionGenerationRequest(ApiSchema):
    experiment_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    horizon: str = Field(min_length=1)


class GenerationMetadataResponse(ApiSchema):
    provider: str
    model: str
    prompt_version: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    latency_ms: int


class DecisionGenerationResponse(ApiSchema):
    decision: DecisionResponse
    generation: GenerationMetadataResponse


def generation_metadata_response(
    generation: GenerationMetadata,
) -> GenerationMetadataResponse:
    return GenerationMetadataResponse(
        provider=generation.provider,
        model=generation.model,
        prompt_version=generation.prompt_version,
        prompt_tokens=generation.prompt_tokens,
        completion_tokens=generation.completion_tokens,
        total_tokens=generation.total_tokens,
        latency_ms=generation.latency_ms,
    )
