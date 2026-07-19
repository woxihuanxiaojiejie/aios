from enum import StrEnum


class ExperimentStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"


class Action(StrEnum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    OBSERVE = "observe"
    NO_TRADE = "no_trade"


class DecisionStatus(StrEnum):
    PROPOSED = "proposed"
    REVIEWED = "reviewed"
    INVALID = "invalid"


class Outcome(StrEnum):
    PROFIT = "profit"
    LOSS = "loss"
    FLAT = "flat"
    INVALID = "invalid"


class LearningType(StrEnum):
    AGENT_WEIGHT_UPDATE = "agent_weight_update"
    PROMPT_UPDATE = "prompt_update"
    RULE_UPDATE = "rule_update"
    MEMORY_UPDATE = "memory_update"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
