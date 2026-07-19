from __future__ import annotations

from fastapi import APIRouter, Query, status

from aios.api.dependencies import LifecycleDep
from aios.api.schemas.common import CompleteExperimentRequest, ListResponse, page
from aios.api.schemas.experiment import (
    ExperimentCreateRequest,
    ExperimentResponse,
    experiment_response,
)
from aios.kernel.experiment import Experiment

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
def create_experiment(
    request: ExperimentCreateRequest,
    lifecycle: LifecycleDep,
) -> ExperimentResponse:
    experiment = Experiment(**request.model_dump())
    return experiment_response(lifecycle.start_experiment(experiment))


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(experiment_id: str, lifecycle: LifecycleDep) -> ExperimentResponse:
    return experiment_response(lifecycle.get_entity(Experiment, experiment_id))


@router.get("", response_model=ListResponse[ExperimentResponse])
def list_experiments(
    lifecycle: LifecycleDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ListResponse[ExperimentResponse]:
    items = [experiment_response(item) for item in lifecycle.list_entities(Experiment)]
    return page(items, limit, offset)


@router.post("/{experiment_id}/complete", response_model=ExperimentResponse)
def complete_experiment(
    experiment_id: str,
    request: CompleteExperimentRequest,
    lifecycle: LifecycleDep,
) -> ExperimentResponse:
    return experiment_response(
        lifecycle.complete_experiment(experiment_id, request.finished_at)
    )
