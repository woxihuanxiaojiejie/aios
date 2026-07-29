import { describe, expect, it } from "vitest";

import {
  displayAction,
  displayDirection,
  displayLearningType,
  displayPageName,
  displayResearchStage,
  displayRuntimeStatus,
  displayStatus,
  displayTriggerMethod,
  technicalValue,
} from "./displayMappings";

describe("displayMappings", () => {
  it("maps common business values to Chinese labels", () => {
    expect(displayPageName("dashboard")).toBe("首页");
    expect(displayStatus("completed")).toBe("已完成");
    expect(displayResearchStage("risk_review")).toBe("反方审查");
    expect(displayAction("buy")).toBe("买入");
    expect(displayDirection("bearish")).toBe("看空");
    expect(displayTriggerMethod("scheduled")).toBe("自动调度");
    expect(displayLearningType("skill_weight_update")).toBe("Skill 权重调整建议");
    expect(displayRuntimeStatus("not_configured")).toBe("未配置");
  });

  it("keeps unknown raw values out of primary UI labels", () => {
    expect(displayStatus("backend_raw_value")).toBe("未知状态");
    expect(displayAction("unexpected_action")).toBe("未知状态");
    expect(displayDirection("unexpected_direction")).toBe("未知状态");
    expect(technicalValue("unexpected_direction")).toBe("unexpected_direction");
  });
});
