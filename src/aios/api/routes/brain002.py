from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Query, status

from aios.api.dependencies import Brain002RegistryDep, LLMAdapterDep, StorageDep
from aios.api.schemas.brain002 import (
    AnalysisExecutionRequest,
    AnalysisExecutionResponse,
    AnalysisTaskCreateRequest,
    AnalysisTaskResponse,
    SkillDefinitionListResponse,
    SkillDefinitionResponse,
    SkillExecutionListResponse,
    SkillResultListResponse,
    analysis_task_response,
    skill_definition_response,
    skill_execution_response,
    skill_result_response,
)
from aios.application.brain002 import (
    ExecutableSkill,
    SkillExecutor,
    SkillRegistry,
    SkillSelector,
)
from aios.kernel.brain002 import AnalysisTask, SkillExecution, SkillResult
from aios.kernel.enums import SkillExecutionStatus
from aios.kernel.evidence import Evidence
from aios.skills.brain002 import (
    AnnouncementRiskSkill,
    MarketSentimentSkill,
    PolicyImpactSkill,
    SectorStrengthSkill,
    TechnicalTrendSkill,
)

router = APIRouter(prefix="/brain/analysis", tags=["brain002-analysis"])


@router.post(
    "/tasks",
    response_model=AnalysisTaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_analysis_task(
    request: AnalysisTaskCreateRequest,
    storage: StorageDep,
) -> AnalysisTaskResponse:
    task = AnalysisTask(**request.model_dump())
    storage.save(task)
    return analysis_task_response(task)


@router.get("/tasks/{task_id}", response_model=AnalysisTaskResponse)
def get_analysis_task(
    task_id: str,
    storage: StorageDep,
) -> AnalysisTaskResponse:
    return analysis_task_response(storage.get(AnalysisTask, task_id))


@router.post(
    "/tasks/{task_id}/execute",
    response_model=AnalysisExecutionResponse,
)
def execute_analysis_task(
    task_id: str,
    request: AnalysisExecutionRequest,
    storage: StorageDep,
    llm_adapter: LLMAdapterDep,
    registry: Brain002RegistryDep,
) -> AnalysisExecutionResponse:
    task = storage.get(AnalysisTask, task_id)
    evidence = tuple(
        storage.get(Evidence, evidence_id) for evidence_id in task.evidence_ids
    )
    selection = SkillSelector(registry).select(task=task, evidence=evidence)
    skills_by_id = _mvp_skills_by_id()
    selected_skills = tuple(
        skills_by_id[skill_id]
        for skill_id in selection.selected_skill_ids
        if skill_id in skills_by_id
    )
    outcome = SkillExecutor(
        llm=llm_adapter,
        model=request.model,
        timeout_seconds=request.timeout_seconds,
        max_attempts=request.max_attempts,
    ).execute(
        task=task,
        skills=selected_skills,
        evidence=evidence,
        market_context=request.market_context,
    )
    for execution in outcome.executions:
        storage.save(execution)
    for result in outcome.results:
        storage.save(result)
    return AnalysisExecutionResponse(
        executions=[skill_execution_response(item) for item in outcome.executions],
        results=[skill_result_response(item) for item in outcome.results],
    )


@router.get("/skills", response_model=SkillDefinitionListResponse)
def list_skills(registry: Brain002RegistryDep) -> SkillDefinitionListResponse:
    return SkillDefinitionListResponse(
        items=[skill_definition_response(item) for item in registry.list()]
    )


@router.get(
    "/skills/{skill_id}/versions",
    response_model=SkillDefinitionListResponse,
)
def list_skill_versions(
    skill_id: str,
    registry: Brain002RegistryDep,
) -> SkillDefinitionListResponse:
    return SkillDefinitionListResponse(
        items=[
            skill_definition_response(item)
            for item in registry.list()
            if item.skill_id == skill_id
        ]
    )


@router.post(
    "/skills/{skill_id}/enable",
    response_model=SkillDefinitionResponse,
)
def enable_skill(
    skill_id: str,
    registry: Brain002RegistryDep,
    version: str = Query(min_length=1),
) -> SkillDefinitionResponse:
    return skill_definition_response(registry.enable(skill_id, version))


@router.post(
    "/skills/{skill_id}/disable",
    response_model=SkillDefinitionResponse,
)
def disable_skill(
    skill_id: str,
    registry: Brain002RegistryDep,
    version: str = Query(min_length=1),
) -> SkillDefinitionResponse:
    return skill_definition_response(registry.disable(skill_id, version))


@router.get("/results", response_model=SkillResultListResponse)
def list_skill_results(
    storage: StorageDep,
    task_id: str | None = None,
) -> SkillResultListResponse:
    executions_by_id = {
        execution.execution_id: execution for execution in storage.list(SkillExecution)
    }
    results = storage.list(SkillResult)
    if task_id is not None:
        results = [
            result
            for result in results
            if executions_by_id[result.execution_id].task_id == task_id
        ]
    return SkillResultListResponse(
        items=[skill_result_response(result) for result in results]
    )


@router.get("/failures", response_model=SkillExecutionListResponse)
def list_failed_skill_executions(storage: StorageDep) -> SkillExecutionListResponse:
    failures = [
        execution
        for execution in storage.list(SkillExecution)
        if execution.status
        in {SkillExecutionStatus.FAILED, SkillExecutionStatus.TIMED_OUT}
    ]
    return SkillExecutionListResponse(
        items=[skill_execution_response(execution) for execution in failures]
    )


def default_brain002_registry() -> SkillRegistry:
    registry = SkillRegistry()
    for skill in _mvp_skills_by_id().values():
        registry.register(skill.definition)
    return registry


def _mvp_skills_by_id() -> dict[str, ExecutableSkill]:
    skills = cast(
        "tuple[ExecutableSkill, ...]",
        (
            TechnicalTrendSkill(),
            SectorStrengthSkill(),
            PolicyImpactSkill(),
            AnnouncementRiskSkill(),
            MarketSentimentSkill(),
        ),
    )
    return {skill.definition.skill_id: skill for skill in skills}
