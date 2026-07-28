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

  it("keeps the existing ResearchWorkbench available at /research", async () => {
    window.history.pushState({}, "", "/research");

    render(<App />);

    expect(
      await screen.findByText("AIOS 人工验收工作台"),
    ).toBeInTheDocument();
  });
});

async function apiResponse(input: RequestInfo | URL) {
  const url = String(input);
  if (url.endsWith("/research/watchlist")) {
    return json({ items: [], total: 0, limit: 50, offset: 0 });
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
