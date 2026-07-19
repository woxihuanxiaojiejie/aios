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


class OutcomeStatus(StrEnum):
    SETTLED = "settled"
    INSUFFICIENT_DATA = "insufficient_data"
    INVALIDATED = "invalidated"


class DirectionalResult(StrEnum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    NEUTRAL = "neutral"
    NOT_APPLICABLE = "not_applicable"


class ReturnResult(StrEnum):
    MET = "met"
    MISSED = "missed"
    NOT_APPLICABLE = "not_applicable"


class RiskResult(StrEnum):
    WITHIN_LIMIT = "within_limit"
    BREACHED = "breached"
    NOT_APPLICABLE = "not_applicable"


class EvaluationFinalResult(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INVALID = "invalid"
    INCONCLUSIVE = "inconclusive"


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
