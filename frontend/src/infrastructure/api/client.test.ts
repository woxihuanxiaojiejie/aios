import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiClient } from "./client";

describe("apiClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reads the API base URL and sends JSON requests through one client", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(json({ ok: true }));
    vi.stubGlobal("fetch", fetchSpy);

    await expect(apiClient.get("/health")).resolves.toEqual({ ok: true });

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/health",
      expect.objectContaining({
        headers: expect.objectContaining({ "content-type": "application/json" }),
      }),
    );
  });

  it("standardizes FastAPI error responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        json({ error: { code: "entity_conflict", message: "duplicate", details: {} } }, 409),
      ),
    );

    await expect(apiClient.post("/research/watchlist", {})).rejects.toMatchObject({
      name: "ApiError",
      status: 409,
      code: "entity_conflict",
      message: "duplicate",
      readableMessage: "A matching record already exists.",
    } satisfies Partial<ApiError>);
  });

  it("turns network failures into readable API errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(apiClient.get("/research/watchlist")).rejects.toMatchObject({
      status: 0,
      code: "network_error",
      readableMessage: "API is unavailable. Check VITE_API_BASE_URL and backend status.",
    });
  });
});

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
