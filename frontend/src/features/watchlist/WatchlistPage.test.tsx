import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App as AntdApp } from "antd";
import { MemoryRouter, Route, Routes, useParams } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { WatchlistPage } from "./WatchlistPage";

const requests: Array<{ url: string; method: string; body: unknown }> = [];
let unavailable = false;
let validationFailure = false;
let conflictFailure = false;
let delayCreate = false;
let items = [watchlistItem({ note: "policy watch" })];

describe("WatchlistPage", () => {
  beforeEach(() => {
    requests.length = 0;
    unavailable = false;
    validationFailure = false;
    conflictFailure = false;
    delayCreate = false;
    items = [watchlistItem({ note: "policy watch" })];
    vi.stubGlobal("fetch", vi.fn(apiResponse));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lists active and archived watchlist items from the backend", async () => {
    renderPage();

    expect(await screen.findByText("600519")).toBeInTheDocument();
    expect(screen.getByText("policy watch")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("tab", { name: "Archived" }));

    expect(await screen.findByText("0700")).toBeInTheDocument();
    expect(
      requests.some(
        (request) =>
          request.url.endsWith("/research/watchlist?status=archived") &&
          request.method === "GET",
      ),
    ).toBe(true);
  });

  it("creates, updates, archives, and restores through real API endpoints", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(await screen.findByLabelText("Symbol"), "000001");
    await user.type(screen.getByLabelText("Market"), "CN");
    await user.type(screen.getByLabelText("Note"), "banking watch");
    await user.click(screen.getByRole("button", { name: "Create" }));

    expect(await screen.findByText("000001")).toBeInTheDocument();
    expect(
      requests.some(
        (request) =>
          request.url.endsWith("/research/watchlist") &&
          request.method === "POST" &&
          JSON.stringify(request.body).includes("000001"),
      ),
    ).toBe(true);

    const row = screen.getByText("000001").closest("tr");
    expect(row).not.toBeNull();
    await user.click(within(row as HTMLTableRowElement).getByRole("button", { name: "Edit" }));
    await user.clear(screen.getByLabelText("Edit note"));
    await user.type(screen.getByLabelText("Edit note"), "updated note");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("updated note")).toBeInTheDocument();
    await user.click(
      within(row as HTMLTableRowElement).getByRole("button", { name: "Archive" }),
    );
    await waitFor(() =>
      expect(
        items.find((item) => item.watchlist_item_id === "wl_new")?.status,
      ).toBe("archived"),
    );
    await user.click(screen.getByRole("tab", { name: "Archived" }));
    expect(await screen.findByText("000001")).toBeInTheDocument();
    const archivedRow = screen.getByText("000001").closest("tr");
    expect(archivedRow).not.toBeNull();
    await user.click(
      within(archivedRow as HTMLTableRowElement).getByRole("button", {
        name: "Restore",
      }),
    );

    await waitFor(() =>
      expect(
        requests.some((request) =>
          request.url.endsWith("/research/watchlist/wl_new/restore"),
        ),
      ).toBe(true),
    );
  });

  it("shows readable 409 and 422 errors", async () => {
    const user = userEvent.setup();
    conflictFailure = true;
    renderPage();

    await user.type(await screen.findByLabelText("Symbol"), "600519");
    await user.type(screen.getByLabelText("Market"), "CN");
    await user.click(screen.getByRole("button", { name: "Create" }));

    expect(await screen.findByText(/already exists/i)).toBeInTheDocument();

    conflictFailure = false;
    validationFailure = true;
    await user.clear(screen.getByLabelText("Symbol"));
    await user.type(screen.getByLabelText("Symbol"), " ");
    await user.click(screen.getByRole("button", { name: "Create" }));

    expect(await screen.findByText(/validation/i)).toBeInTheDocument();
  });

  it("does not blank the page when the API is unavailable", async () => {
    unavailable = true;

    renderPage();

    expect(await screen.findByText(/API is unavailable/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Watchlist" })).toBeInTheDocument();
  });

  it("prevents duplicate submit clicks while creating", async () => {
    const user = userEvent.setup();
    delayCreate = true;
    renderPage();

    await user.type(await screen.findByLabelText("Symbol"), "000002");
    await user.type(screen.getByLabelText("Market"), "CN");
    const create = screen.getByRole("button", { name: "Create" });
    await user.click(create);

    expect(create).toBeDisabled();
    delayCreate = false;
  });

  it("navigates to the real Research Run after manual run succeeds", async () => {
    const user = userEvent.setup();
    renderPage();

    const row = (await screen.findByText("600519")).closest("tr");
    expect(row).not.toBeNull();
    await user.click(
      within(row as HTMLTableRowElement).getByRole("button", {
        name: "Run research",
      }),
    );

    expect(await screen.findByTestId("run-route")).toHaveTextContent("run_watchlist");
  });
});

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <AntdApp>
        <MemoryRouter initialEntries={["/watchlist"]}>
          <Routes>
            <Route path="/watchlist" element={<WatchlistPage />} />
            <Route path="/research/:runId" element={<RunRoute />} />
          </Routes>
        </MemoryRouter>
      </AntdApp>
    </QueryClientProvider>,
  );
}

function RunRoute() {
  const { runId } = useParams();
  return <span data-testid="run-route">{runId}</span>;
}

async function apiResponse(input: RequestInfo | URL, init?: RequestInit) {
  const url = String(input);
  const method = init?.method ?? "GET";
  const body = init?.body ? JSON.parse(String(init.body)) : null;
  requests.push({ url, method, body });

  if (unavailable) {
    throw new TypeError("Failed to fetch");
  }
  if (method === "GET" && url.endsWith("/research/watchlist")) {
    return json({ items: items.filter((item) => item.status === "active"), total: 1, limit: 50, offset: 0 });
  }
  if (method === "GET" && url.endsWith("/research/watchlist?status=archived")) {
    return json({
      items: [
        ...items.filter((item) => item.status === "archived"),
        watchlistItem({
          watchlist_item_id: "wl_archived",
          symbol: "0700",
          market: "HK",
          status: "archived",
          archived_at: "2026-07-28T00:00:00Z",
        }),
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });
  }
  if (method === "POST" && url.endsWith("/research/watchlist")) {
    if (delayCreate) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    if (conflictFailure) {
      return jsonError(409, "entity_conflict", "active watchlist item already exists");
    }
    if (validationFailure) {
      return jsonError(422, "validation_error", "validation failed");
    }
    const created = watchlistItem({
      watchlist_item_id: "wl_new",
      symbol: String(body.symbol).trim(),
      market: String(body.market).trim(),
      note: body.note,
    });
    items = [created, ...items];
    return json(created, 201);
  }
  if (method === "PATCH" && url.includes("/research/watchlist/wl_new")) {
    items = items.map((item) =>
      item.watchlist_item_id === "wl_new" ? { ...item, note: body.note } : item,
    );
    return json(items.find((item) => item.watchlist_item_id === "wl_new"));
  }
  if (method === "POST" && url.endsWith("/research/watchlist/wl_new/archive")) {
    items = items.map((item) =>
      item.watchlist_item_id === "wl_new"
        ? { ...item, status: "archived", archived_at: "2026-07-28T00:00:00Z" }
        : item,
    );
    return json(items.find((item) => item.watchlist_item_id === "wl_new"));
  }
  if (method === "POST" && url.endsWith("/research/watchlist/wl_new/restore")) {
    items = items.map((item) =>
      item.watchlist_item_id === "wl_new"
        ? { ...item, status: "active", archived_at: null }
        : item,
    );
    return json(items.find((item) => item.watchlist_item_id === "wl_new"));
  }
  if (method === "POST" && url.endsWith("/research/watchlist/wl_existing/run")) {
    return json({
      run: {
        run_id: "run_watchlist",
        research_session_id: "rs_watchlist",
        watchlist_item_id: "wl_existing",
        symbol: "600519",
        research_window_key: "600519:2026-07-28:3",
        current_stage: "session",
        status: "running",
        vibe_run_id: null,
        workflow: "investment_committee",
        input_params: {},
        raw_output_reference: null,
        failed_stage: null,
        error_type: null,
        error: null,
        finished_at: null,
        created_at: "2026-07-28T00:00:00Z",
        updated_at: "2026-07-28T00:00:00Z",
      },
      trade_plan: null,
      simulated_execution: null,
    });
  }
  return json({});
}

function watchlistItem(
  overrides: Partial<Record<string, unknown>> = {},
): Record<string, unknown> {
  return {
    watchlist_item_id: "wl_existing",
    symbol: "600519",
    market: "CN",
    note: null,
    status: "active",
    auto_research_enabled: false,
    research_horizon_days: 3,
    schedule_time: "15:00:00",
    schedule_timezone: "Asia/Shanghai",
    next_run_at: null,
    last_run_at: null,
    created_at: "2026-07-28T00:00:00Z",
    updated_at: "2026-07-28T00:00:00Z",
    archived_at: null,
    ...overrides,
  };
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function jsonError(status: number, code: string, message: string) {
  return json({ error: { code, message, details: {} } }, status);
}
