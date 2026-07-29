export type DisplayValue = string | null | undefined;

const PAGE_NAMES: Record<string, string> = {
  dashboard: "首页",
  home: "首页",
  research: "研究",
  decision: "决策",
  decisions: "决策",
  execution: "模拟执行",
  settlement: "结果结算",
  review: "复盘",
  reviews: "复盘",
  learning: "学习",
  learning_proposal: "学习建议",
  system: "系统",
};

const STATUS_NAMES: Record<string, string> = {
  active: "启用",
  archived: "已归档",
  completed: "已完成",
  failed: "失败",
  running: "运行中",
  pending: "等待处理",
  proposed: "已提出",
  reviewed: "已复核",
  invalid: "无效",
  ready: "可执行",
  no_trade: "不交易",
  expired: "已过期",
  cancelled: "已取消",
  waiting_settlement: "等待结算",
  settled: "已结算",
  insufficient_data: "数据不足",
  invalidated: "已失效",
  approved: "已批准",
  rejected: "已拒绝",
  deferred: "已暂缓",
  succeeded: "成功",
  timed_out: "超时",
  healthy: "正常",
  degraded: "降级",
  unavailable: "不可用",
  not_configured: "未配置",
  unknown: "未知",
  correct: "正确",
  incorrect: "错误",
  neutral: "中性",
  not_applicable: "不适用",
  met: "达到预期",
  missed: "未达预期",
  within_limit: "风控有效",
  breached: "突破风控",
  pass: "通过",
  fail: "未通过",
  inconclusive: "无法判断",
  profit: "盈利",
  loss: "亏损",
  flat: "持平",
};

const RESEARCH_STAGE_NAMES: Record<string, string> = {
  session: "研究会话",
  evidence: "证据材料",
  vibe_research: "外部研究",
  agent_reports: "五项独立分析",
  hypotheses: "初始假设",
  debate: "冲突识别",
  proposal: "讨论修订",
  risk_review: "反方审查",
  decision: "最终决策",
  completed: "已完成",
  failed: "失败",
  collecting_evidence: "采集证据",
  evidence_ready: "证据就绪",
  hypothesis_ready: "假设就绪",
  skills_running: "分析中",
  discussion_ready: "讨论完成",
  decision_ready: "决策完成",
  trade_plan_ready: "交易计划完成",
  waiting_execution: "等待模拟执行",
  waiting_settlement: "等待结算",
  settled: "已结算",
  reviewed: "已复盘",
  learning_proposed: "已提出学习建议",
};

const ACTION_NAMES: Record<string, string> = {
  buy: "买入",
  sell: "卖出",
  hold: "观察",
  observe: "观察",
  watch: "观察",
  no_trade: "不交易",
};

const DIRECTION_NAMES: Record<string, string> = {
  bullish: "看多",
  bearish: "看空",
  neutral: "中性",
  no_trade: "不交易",
  uncertain: "不确定",
  support: "支持",
  oppose: "反对",
};

const TRIGGER_NAMES: Record<string, string> = {
  manual: "人工触发",
  scheduled: "自动调度",
  scheduler: "自动调度",
  investment_committee: "研究流程",
};

const LEARNING_TYPE_NAMES: Record<string, string> = {
  agent_weight_update: "Agent 权重调整建议",
  skill_weight_update: "Skill 权重调整建议",
  prompt_update: "提示词调整建议",
  rule_update: "规则调整建议",
  hypothesis_update: "假设调整建议",
  memory_update: "记忆更新建议",
};

const PROVIDER_STATUS_NAMES: Record<string, string> = {
  configured: "已配置",
  not_configured: "未配置",
  invalid_configuration: "配置无效",
  healthy: "正常",
  degraded: "配置异常",
  unavailable: "不可用",
  unknown: "未知",
};

export function displayPageName(value: DisplayValue) {
  return displayFrom(PAGE_NAMES, value, "未知页面");
}

export function displayStatus(value: DisplayValue) {
  return displayFrom(STATUS_NAMES, value);
}

export function displayResearchStage(value: DisplayValue) {
  return displayFrom(RESEARCH_STAGE_NAMES, value);
}

export function displayAction(value: DisplayValue) {
  return displayFrom(ACTION_NAMES, value);
}

export function displayDirection(value: DisplayValue) {
  return displayFrom(DIRECTION_NAMES, value);
}

export function displayTriggerMethod(value: DisplayValue) {
  return displayFrom(TRIGGER_NAMES, value);
}

export function displayLearningType(value: DisplayValue) {
  return displayFrom(LEARNING_TYPE_NAMES, value, "未知建议类型");
}

export function displayRuntimeStatus(value: DisplayValue) {
  return displayFrom(STATUS_NAMES, value);
}

export function displayProviderStatus(value: DisplayValue) {
  return displayFrom(PROVIDER_STATUS_NAMES, value);
}

export function technicalValue(value: DisplayValue) {
  return value === null || value === undefined || value === "" ? "-" : String(value);
}

function displayFrom(
  mapping: Record<string, string>,
  value: DisplayValue,
  unknown = "未知状态",
) {
  if (value === null || value === undefined || value === "") return "-";
  return mapping[String(value)] ?? unknown;
}
