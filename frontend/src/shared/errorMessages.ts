import { ApiError } from "../infrastructure/api/client";

export type UserReadableErrorInfo = {
  message: string;
  technical: {
    code: string | null;
    status: number | null;
    message: string;
    details: unknown;
  };
};

const ERROR_MESSAGES: Record<string, string> = {
  network_error: "无法连接 AIOS 后端，请检查后端服务是否运行。",
  entity_not_found: "没有找到对应记录，可能已被删除或当前环境数据不一致。",
  request_validation_error: "提交内容格式不正确，请检查输入后重试。",
  validation_error: "提交内容格式不正确，请检查输入后重试。",
  validation_failed: "提交内容没有通过业务校验，请检查输入后重试。",
  entity_conflict: "相同记录已经存在，请检查后重试。",
  invalid_state_transition: "当前状态不允许执行该操作，请刷新页面后重试。",
  market_data_unsupported_symbol:
    "当前市场不支持该股票代码，请检查股票代码和市场是否匹配。",
  provider_unavailable: "数据或模型服务暂时不可用，请稍后重试或检查系统状态。",
  evidence_collection_error: "证据采集失败，当前研究未获得足够数据。",
  storage_operation_error: "数据存取失败，请稍后重试或检查系统状态。",
  request_failed: "请求失败，请稍后重试或检查系统状态。",
};

export function userReadableError(error: unknown): UserReadableErrorInfo {
  if (error instanceof ApiError) {
    return {
      message: ERROR_MESSAGES[error.code] ?? ERROR_MESSAGES.request_failed,
      technical: {
        code: error.code,
        status: error.status,
        message: error.message,
        details: error.details,
      },
    };
  }
  return {
    message: ERROR_MESSAGES.request_failed,
    technical: {
      code: null,
      status: null,
      message: error instanceof Error ? error.message : String(error),
      details: null,
    },
  };
}
