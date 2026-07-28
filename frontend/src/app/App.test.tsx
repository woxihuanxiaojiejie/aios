import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

describe("App routing", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(apiResponse));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.history.replaceState({}, "", "/");
  });

  it("redirects / to the watchlist page", async () => {
    window.history.pushState({}, "", "/");

    render(<App />);

    await waitFor(() => expect(window.location.pathname).toBe("/watchlist"));
    expect(
      await screen.findByRole("heading", { name: "Watchlist" }),
    ).toBeInTheDocument();
  });

  it("serves the Research Runs list at /research", async () => {
    window.history.pushState({}, "", "/research");

    render(<App />);

    expect(await screen.findByText("Research Runs")).toBeInTheDocument();
  });

  it("keeps the existing ResearchWorkbench available at /research/new", async () => {
    window.history.pushState({}, "", "/research/new");

    render(<App />);

    expect(
      await screen.findByText("AIOS 人工验收工作台"),
    ).toBeInTheDocument();
  });

  it("serves the execution and settlement explorer routes", async () => {
    window.history.pushState({}, "", "/executions");
    const { unmount } = render(<App />);

    expect(await screen.findByText("Simulated Executions")).toBeInTheDocument();
    unmount();

    window.history.pushState({}, "", "/settlements");
    const settlements = render(<App />);

    expect(await screen.findByText("Settlements")).toBeInTheDocument();
    settlements.unmount();

    window.history.pushState({}, "", "/learning-proposals");
    render(<App />);

    expect(await screen.findByText("Learning Proposals")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve|reject|apply/i })).not.toBeInTheDocument();
  });
});

async function apiResponse(input: RequestInfo | URL) {
  const url = String(input);
  if (url.endsWith("/research/watchlist")) {
    return json({ items: [], total: 0, limit: 50, offset: 0 });
  }
  if (url.includes("/research/runs")) {
    return json({ items: [], total: 0, limit: 10, offset: 0, count: 0 });
  }
  if (url.includes("/simulated-executions")) {
    return json({ items: [], total: 0, page: 1, page_size: 10, count: 0 });
  }
  if (url.includes("/settlements")) {
    return json({ items: [], total: 0, page: 1, page_size: 10, count: 0 });
  }
  if (url.includes("/learnings")) {
    return json({ items: [], total: 0, limit: 50, offset: 0, count: 0 });
  }
  if (url.endsWith("/evidence") || url.endsWith("/research/sessions")) {
    return json({ items: [], total: 0, limit: 50, offset: 0 });
  }
  return json({ items: [], total: 0, limit: 50, offset: 0 });
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
