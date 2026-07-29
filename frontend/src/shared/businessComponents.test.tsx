import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  BusinessStatusTag,
  CopyableId,
  EmptyBusinessState,
  LongText,
  TechnicalDetails,
  UserReadableError,
} from "./businessComponents";

describe("businessComponents", () => {
  it("renders Chinese business status labels", () => {
    render(<BusinessStatusTag value="completed" />);

    expect(screen.getByText("已完成")).toBeInTheDocument();
    expect(screen.queryByText("completed")).not.toBeInTheDocument();
  });

  it("keeps raw technical values inside technical details", () => {
    render(<TechnicalDetails data={{ status: "completed", id: "run_1" }} />);

    expect(screen.queryByText(/completed/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("技术详情"));
    expect(screen.getByText(/completed/)).toBeInTheDocument();
  });

  it("renders long text as summary with expansion", () => {
    render(<LongText text="这是一段很长的研究结论，需要默认收起但允许用户展开阅读全文。" maxLength={12} />);

    expect(screen.getByText(/这是一段很长的/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "展开全文" }));
    expect(screen.getByText(/允许用户展开阅读全文/)).toBeInTheDocument();
  });

  it("renders low-priority copyable ids and Chinese empty/error states", () => {
    render(
      <>
        <CopyableId value="run_123" />
        <EmptyBusinessState description="暂无研究记录" />
        <UserReadableError error={new Error("raw failure")} />
      </>,
    );

    expect(screen.getByText("内部编号")).toBeInTheDocument();
    expect(screen.getByText("暂无研究记录")).toBeInTheDocument();
    expect(screen.getByText("请求失败，请稍后重试或检查系统状态。")).toBeInTheDocument();
  });
});
