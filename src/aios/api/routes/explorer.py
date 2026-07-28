from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from aios.api.dependencies import LifecycleDep
from aios.api.schemas.explorer import (
    ExecutionListItemResponse,
    ExplorerDetailResponse,
    ExplorerListResponse,
    SettlementListItemResponse,
    execution_list_response,
    explorer_detail_response,
    settlement_list_response,
)
from aios.application.explorer import ExecutionSettlementExplorer

executions_router = APIRouter(
    prefix="/simulated-executions",
    tags=["simulated-executions"],
)
settlements_router = APIRouter(prefix="/settlements", tags=["settlements"])


@executions_router.get(
    "",
    response_model=ExplorerListResponse[ExecutionListItemResponse],
)
def list_simulated_executions(
    lifecycle: LifecycleDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    symbol: Annotated[str | None, Query(min_length=1)] = None,
    market: Annotated[str | None, Query(min_length=1)] = None,
    status: Annotated[str | None, Query(min_length=1)] = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    sort: str = "-created_at",
) -> ExplorerListResponse[ExecutionListItemResponse]:
    return execution_list_response(
        ExecutionSettlementExplorer(lifecycle.storage).list_executions(
            page=page,
            page_size=page_size,
            symbol=symbol,
            market=market,
            status=status,
            created_from=created_from,
            created_to=created_to,
            sort=sort,
        )
    )


@executions_router.get(
    "/{execution_id}",
    response_model=ExplorerDetailResponse,
)
def get_simulated_execution_detail(
    execution_id: str,
    lifecycle: LifecycleDep,
) -> ExplorerDetailResponse:
    return explorer_detail_response(
        ExecutionSettlementExplorer(lifecycle.storage).execution_detail(execution_id)
    )


@settlements_router.get(
    "",
    response_model=ExplorerListResponse[SettlementListItemResponse],
)
def list_settlements(
    lifecycle: LifecycleDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    symbol: Annotated[str | None, Query(min_length=1)] = None,
    market: Annotated[str | None, Query(min_length=1)] = None,
    status: Annotated[str | None, Query(min_length=1)] = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    sort: str = "-settled_at",
) -> ExplorerListResponse[SettlementListItemResponse]:
    return settlement_list_response(
        ExecutionSettlementExplorer(lifecycle.storage).list_settlements(
            page=page,
            page_size=page_size,
            symbol=symbol,
            market=market,
            status=status,
            created_from=created_from,
            created_to=created_to,
            sort=sort,
        )
    )


@settlements_router.get(
    "/{settlement_id}",
    response_model=ExplorerDetailResponse,
)
def get_settlement_detail(
    settlement_id: str,
    lifecycle: LifecycleDep,
) -> ExplorerDetailResponse:
    return explorer_detail_response(
        ExecutionSettlementExplorer(lifecycle.storage).settlement_detail(settlement_id)
    )
