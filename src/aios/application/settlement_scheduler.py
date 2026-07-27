from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aios.adapters.market_data import MarketDataAdapter
from aios.adapters.storage import Storage
from aios.application.research_lifecycle import ResearchLifecycleService
from aios.application.settlement import SettlementResult, SettlementService
from aios.kernel.enums import ExecutionStatus
from aios.kernel.execution import SimulatedExecution
from aios.kernel.trade_plan import TradePlan


@dataclass(frozen=True)
class SettlementSchedulerError:
    execution_id: str
    error_type: str
    error_message: str


@dataclass(frozen=True)
class SettlementSchedulerResult:
    settled: tuple[SettlementResult, ...]
    errors: tuple[SettlementSchedulerError, ...]


class SettlementSchedulerService:
    def __init__(
        self,
        *,
        storage: Storage,
        market_data_adapter: MarketDataAdapter,
    ) -> None:
        self._storage = storage
        self._market_data_adapter = market_data_adapter

    def run_due_once(self, *, as_of: datetime) -> SettlementSchedulerResult:
        service = SettlementService(
            lifecycle=ResearchLifecycleService(self._storage),
            market_data_adapter=self._market_data_adapter,
        )
        settled: list[SettlementResult] = []
        errors: list[SettlementSchedulerError] = []
        for execution in self._due_executions(as_of):
            try:
                settled.append(service.settle_execution(execution.execution_id))
            except Exception as exc:
                errors.append(
                    SettlementSchedulerError(
                        execution_id=execution.execution_id,
                        error_type=type(exc).__name__,
                        error_message=str(exc),
                    )
                )
        return SettlementSchedulerResult(
            settled=tuple(settled),
            errors=tuple(errors),
        )

    def _due_executions(self, as_of: datetime) -> list[SimulatedExecution]:
        due: list[SimulatedExecution] = []
        for execution in self._storage.list(SimulatedExecution):
            if self._storage.get_settlement_outcome_by_execution_id(
                execution.execution_id
            ):
                continue
            if execution.execution_status is not ExecutionStatus.WAITING_SETTLEMENT:
                continue
            plan = self._storage.get(TradePlan, execution.trade_plan_id)
            if plan.expiry <= as_of:
                due.append(execution)
        return due
