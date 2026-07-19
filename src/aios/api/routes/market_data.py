from __future__ import annotations

from fastapi import APIRouter, status

from aios.adapters.market_data import MarketDataAdapter
from aios.api.dependencies import (
    BaoStockMarketDataAdapterDep,
    LifecycleDep,
    MarketDataAdapterDep,
)
from aios.api.schemas.market_data import (
    MarketBarPreviewResponse,
    MarketDataImportRequest,
    MarketDataImportResponse,
    market_bar_response,
)
from aios.application.market_evidence import MarketEvidenceImportService
from aios.workflows.decision_lifecycle import DecisionLifecycleService

router = APIRouter(prefix="/market-data/akshare/daily-bars", tags=["market-data"])
baostock_router = APIRouter(
    prefix="/market-data/baostock/daily-bars",
    tags=["market-data"],
)


@router.post(
    "/import",
    response_model=MarketDataImportResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_akshare_daily_bars(
    request: MarketDataImportRequest,
    lifecycle: LifecycleDep,
    adapter: MarketDataAdapterDep,
) -> MarketDataImportResponse:
    return _import_daily_bars(request, lifecycle, adapter)


@router.post("/preview", response_model=MarketBarPreviewResponse)
def preview_akshare_daily_bars(
    request: MarketDataImportRequest,
    lifecycle: LifecycleDep,
    adapter: MarketDataAdapterDep,
) -> MarketBarPreviewResponse:
    return _preview_daily_bars(request, lifecycle, adapter)


@baostock_router.post(
    "/import",
    response_model=MarketDataImportResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_baostock_daily_bars(
    request: MarketDataImportRequest,
    lifecycle: LifecycleDep,
    adapter: BaoStockMarketDataAdapterDep,
) -> MarketDataImportResponse:
    return _import_daily_bars(request, lifecycle, adapter)


@baostock_router.post("/preview", response_model=MarketBarPreviewResponse)
def preview_baostock_daily_bars(
    request: MarketDataImportRequest,
    lifecycle: LifecycleDep,
    adapter: BaoStockMarketDataAdapterDep,
) -> MarketBarPreviewResponse:
    return _preview_daily_bars(request, lifecycle, adapter)


def _import_daily_bars(
    request: MarketDataImportRequest,
    lifecycle: DecisionLifecycleService,
    adapter: MarketDataAdapter,
) -> MarketDataImportResponse:
    service = MarketEvidenceImportService(adapter=adapter, lifecycle=lifecycle)
    result = service.import_daily_bars(
        symbol=request.symbol,
        start_date=request.start_date,
        end_date=request.end_date,
        adjustment=request.adjustment,
    )
    return MarketDataImportResponse(
        symbol=result.symbol,
        requested=result.requested,
        created=result.created,
        existing=result.existing,
        evidence_ids=result.evidence_ids,
    )


def _preview_daily_bars(
    request: MarketDataImportRequest,
    lifecycle: DecisionLifecycleService,
    adapter: MarketDataAdapter,
) -> MarketBarPreviewResponse:
    service = MarketEvidenceImportService(adapter=adapter, lifecycle=lifecycle)
    bars = service.preview_daily_bars(
        symbol=request.symbol,
        start_date=request.start_date,
        end_date=request.end_date,
        adjustment=request.adjustment,
    )
    return MarketBarPreviewResponse(
        items=[market_bar_response(bar) for bar in bars],
        count=len(bars),
    )
