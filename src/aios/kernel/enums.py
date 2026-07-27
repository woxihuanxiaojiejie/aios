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


class TradePlanStatus(StrEnum):
    READY = "ready"
    NO_TRADE = "no_trade"
    INVALID = "invalid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


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
    SKILL_WEIGHT_UPDATE = "skill_weight_update"
    PROMPT_UPDATE = "prompt_update"
    RULE_UPDATE = "rule_update"
    HYPOTHESIS_UPDATE = "hypothesis_update"
    MEMORY_UPDATE = "memory_update"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class WatchlistStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ResearchSessionStatus(StrEnum):
    CREATED = "created"
    COLLECTING_EVIDENCE = "collecting_evidence"
    EVIDENCE_READY = "evidence_ready"
    HYPOTHESIS_READY = "hypothesis_ready"
    SKILLS_RUNNING = "skills_running"
    DISCUSSION_READY = "discussion_ready"
    RISK_REVIEW = "risk_review"
    DECISION_READY = "decision_ready"
    TRADE_PLAN_READY = "trade_plan_ready"
    WAITING_EXECUTION = "waiting_execution"
    WAITING_SETTLEMENT = "waiting_settlement"
    SETTLED = "settled"
    REVIEWED = "reviewed"
    LEARNING_PROPOSED = "learning_proposed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRole(StrEnum):
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    NEWS = "news"
    SENTIMENT = "sentiment"
    CAPITAL_FLOW = "capital_flow"


class AgentReportStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class HypothesisStatus(StrEnum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    REJECTED = "rejected"
    INVALIDATED = "invalidated"


class DebateStatus(StrEnum):
    OPEN = "open"
    ASSEMBLED = "assembled"
    CANCELLED = "cancelled"


class DebateStance(StrEnum):
    SUPPORT = "support"
    OPPOSE = "oppose"
    NEUTRAL = "neutral"


class ResearchConclusion(StrEnum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    WATCH = "watch"
    NO_TRADE = "no_trade"
    INVALID = "invalid"


class RiskVerdict(StrEnum):
    APPROVE = "approve"
    REDUCE_CONFIDENCE = "reduce_confidence"
    REDUCE_POSITION = "reduce_position"
    MODIFY_CONDITIONS = "modify_conditions"
    DOWNGRADE = "downgrade"
    VETO = "veto"


class SkillStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


class SkillExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class SkillDirection(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    UNCERTAIN = "uncertain"


class DecisionDirection(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    NO_TRADE = "no_trade"


class ExecutionStatus(StrEnum):
    WAITING_SETTLEMENT = "waiting_settlement"
    NOT_FILLED = "not_filled"


class ExecutionExitReason(StrEnum):
    TARGET = "target"
    STOP = "stop"
    EXPIRY = "expiry"
    NOT_FILLED = "not_filled"


class EvaluationScore(StrEnum):
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
