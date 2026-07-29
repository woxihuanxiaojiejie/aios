import { describe, expect, it } from "vitest";

import { ApiError } from "../infrastructure/api/client";
import { userReadableError } from "./errorMessages";

describe("errorMessages", () => {
  it("maps backend error codes to user-readable Chinese messages", () => {
    const error = new ApiError({
      status: 400,
      code: "market_data_unsupported_symbol",
      message: "UnsupportedMarketSymbolError: bad symbol",
    });

    expect(userReadableError(error).message).toBe(
      "当前市场不支持该股票代码，请检查股票代码和市场是否匹配。",
    );
    expect(userReadableError(error).technical.code).toBe(
      "market_data_unsupported_symbol",
    );
  });

  it("uses a Chinese fallback for unknown errors", () => {
    expect(userReadableError(new Error("raw backend failure")).message).toBe(
      "请求失败，请稍后重试或检查系统状态。",
    );
  });
});
