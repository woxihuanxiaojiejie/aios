import { describe, expect, it, vi } from "vitest";

import { createAiosDataProvider } from "./dataProvider";

describe("createAiosDataProvider", () => {
  it("maps watchlist CRUD actions to backend-supported endpoints", async () => {
    const client = {
      get: vi.fn().mockResolvedValue({ items: [], total: 0 }),
      post: vi.fn().mockResolvedValue({ watchlist_item_id: "wl_1" }),
      patch: vi.fn().mockResolvedValue({ watchlist_item_id: "wl_1" }),
      delete: vi.fn(),
    };
    const dataProvider = createAiosDataProvider(client);

    await dataProvider.getList({
      resource: "watchlist",
      pagination: { currentPage: 1, pageSize: 50 },
    });
    await dataProvider.create({
      resource: "watchlist",
      variables: { symbol: "600519", market: "CN" },
    });
    await dataProvider.update({
      resource: "watchlist",
      id: "wl_1",
      variables: { note: "updated" },
    });
    await dataProvider.custom?.({
      url: "/research/watchlist/wl_1/archive",
      method: "post",
    });

    expect(client.get).toHaveBeenCalledWith("/research/watchlist?limit=50&offset=0");
    expect(client.post).toHaveBeenCalledWith("/research/watchlist", {
      symbol: "600519",
      market: "CN",
    });
    expect(client.patch).toHaveBeenCalledWith("/research/watchlist/wl_1", {
      note: "updated",
    });
    expect(client.post).toHaveBeenCalledWith("/research/watchlist/wl_1/archive", undefined);
  });
});
