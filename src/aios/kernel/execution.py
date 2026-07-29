from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import ClassVar

from pydantic import Field, field_validator, model_validator

from aios.kernel.base import KernelModel, ensure_utc, new_id, utc_now
from aios.kernel.enums import DecisionDirection, ExecutionExitReason, ExecutionStatus


class SimulatedExecution(KernelModel):
    id_field: ClassVar[str] = "execution_id"

    execution_id: str = Field(default_factory=lambda: new_id("sx_"))
    trade_plan_id: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)
    research_session_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    direction: DecisionDirection
    execution_status: ExecutionStatus
    execution_date: date | None = None
    market_bar_id: str | None = Field(default=None, min_length=1)
    market_data_source: str | None = Field(default=None, min_length=1)
    planned_entry: str = Field(min_length=1)
    executed_entry: Decimal | None = None
    executed_exit: Decimal | None = None
    position_size: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    fee: Decimal = Field(ge=Decimal("0"))
    slippage: Decimal = Field(ge=Decimal("0"))
    realized_return: Decimal | None = None
    exit_reason: ExecutionExitReason
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        return ensure_utc(value)

    @field_validator(
        "executed_entry",
        "executed_exit",
        "position_size",
        "fee",
        "slippage",
        "realized_return",
        mode="before",
    )
    @classmethod
    def validate_decimal(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))

    @model_validator(mode="after")
    def validate_execution_payload(self) -> SimulatedExecution:
        if self.updated_at < self.created_at:
            msg = "updated_at must not be earlier than created_at"
            raise ValueError(msg)
        if self.execution_status is ExecutionStatus.NOT_FILLED:
            if any(
                value is not None
                for value in (
                    self.execution_date,
                    self.market_bar_id,
                    self.market_data_source,
                    self.executed_entry,
                    self.executed_exit,
                    self.realized_return,
                )
            ):
                msg = "not_filled execution must not contain fill prices"
                raise ValueError(msg)
            if self.exit_reason is not ExecutionExitReason.NOT_FILLED:
                msg = "not_filled execution requires not_filled exit_reason"
                raise ValueError(msg)
        else:
            required = {
                "execution_date": self.execution_date,
                "market_bar_id": self.market_bar_id,
                "market_data_source": self.market_data_source,
                "executed_entry": self.executed_entry,
                "executed_exit": self.executed_exit,
                "realized_return": self.realized_return,
            }
            missing = [name for name, value in required.items() if value is None]
            if missing:
                msg = f"filled execution requires: {', '.join(missing)}"
                raise ValueError(msg)
            if self.executed_entry is not None and self.executed_entry <= 0:
                msg = "executed_entry must be positive"
                raise ValueError(msg)
            if self.executed_exit is not None and self.executed_exit <= 0:
                msg = "executed_exit must be positive"
                raise ValueError(msg)
        return self
